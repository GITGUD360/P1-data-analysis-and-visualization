"""
clean_data.py
-------------
Cleans the raw NOAA files and builds two tables that the analysis uses:

1. data/processed/daily_clean.csv  - one row per station per day
2. data/processed/annual_metrics.csv - one row per station per year with all
   the yearly numbers (mean temperature, hot days, rainfall, ...)

Cleaning steps
  * NOAA stores temperature in tenths of a degree C and rain in tenths of a mm.
    We convert to degrees F and inches.
  * Every value has a quality flag. If NOAA's quality check flagged a value
    (the 2nd field of the *_ATTRIBUTES column is not blank) we throw it away.
  * Days where the high is lower than the low are impossible -> removed.
  * A year is only used if it has at least 330 valid days, otherwise missing
    days could bias the yearly totals.
"""

import numpy as np
import pandas as pd

import config


# ---------------------------------------------------------------------------
# Daily cleaning
# ---------------------------------------------------------------------------
def quality_failed(attributes):
    """True where NOAA's quality flag (2nd item of 'M,Q,S,time') is set."""
    q_flag = attributes.fillna("").str.split(",").str[1].fillna("").str.strip()
    return q_flag != ""


def clean_station(station_id):
    """Read one raw station file and return a tidy, cleaned DataFrame."""
    raw = pd.read_csv(config.RAW_DIR / f"{station_id}.csv", low_memory=False)
    city, region = config.STATIONS[station_id]

    df = pd.DataFrame({
        "station": station_id,
        "city": city,
        "region": region,
        "lat": raw["LATITUDE"],
        "lon": raw["LONGITUDE"],
        "date": pd.to_datetime(raw["DATE"]),
    })

    flagged = {}
    for col in ["TMAX", "TMIN", "PRCP"]:
        values = pd.to_numeric(raw[col], errors="coerce")
        bad = quality_failed(raw[f"{col}_ATTRIBUTES"]) & values.notna()
        flagged[col] = int(bad.sum())
        df[col] = values.where(~bad)

    # unit conversion: tenths of C -> F, tenths of mm -> inches
    df["tmax_f"] = df.pop("TMAX") / 10 * 9 / 5 + 32
    df["tmin_f"] = df.pop("TMIN") / 10 * 9 / 5 + 32
    df["prcp_in"] = df.pop("PRCP") / 10 / 25.4

    impossible = df["tmax_f"] < df["tmin_f"]
    df.loc[impossible, ["tmax_f", "tmin_f"]] = np.nan
    df["tavg_f"] = (df["tmax_f"] + df["tmin_f"]) / 2

    df["year"] = df["date"].dt.year
    df = df[(df["year"] >= config.START_YEAR) & (df["year"] <= config.END_YEAR)]

    quality = {
        "station": station_id, "city": city, "region": region,
        "lat": df["lat"].iloc[0], "lon": df["lon"].iloc[0],
        "days_in_file": len(df),
        "tmax_flagged_removed": flagged["TMAX"],
        "tmin_flagged_removed": flagged["TMIN"],
        "prcp_flagged_removed": flagged["PRCP"],
        "impossible_days_removed": int(impossible.sum()),
        "pct_missing_temp": round(100 * df["tavg_f"].isna().mean(), 2),
        "pct_missing_rain": round(100 * df["prcp_in"].isna().mean(), 2),
    }
    return df.reset_index(drop=True), quality


# ---------------------------------------------------------------------------
# Yearly metrics
# ---------------------------------------------------------------------------
def longest_run(mask):
    """Length of the longest run of consecutive True values."""
    best = current = 0
    for value in mask:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def freeze_season(year_df):
    """Day-of-year of the last spring freeze and the first fall freeze."""
    doy = year_df["date"].dt.dayofyear
    freeze = year_df["tmin_f"] <= config.FREEZE_F
    spring = doy[freeze & (doy < 182)]   # before July 1
    fall = doy[freeze & (doy >= 182)]    # after July 1
    last_spring = spring.max() if len(spring) else 1     # no freeze at all -> Jan 1
    first_fall = fall.min() if len(fall) else 366        # no freeze -> Dec 31
    return last_spring, first_fall


def year_metrics(year_df):
    """All the yearly numbers for one station in one year."""
    temp_days = year_df["tavg_f"].notna().sum()
    rain_days = year_df["prcp_in"].notna().sum()
    out = {"temp_days": temp_days, "rain_days": rain_days}
    for col in ["tavg_f", "tmax_f", "tmin_f", "hot_days", "warm_nights", "freeze_days",
                "last_spring_freeze_doy", "first_fall_freeze_doy", "freeze_free_days",
                "rain_total_in", "wet_days", "heavy_rain_days", "max_1day_rain_in",
                "pct_rain_from_1in_days", "longest_dry_spell"]:
        out[col] = np.nan   # stays missing if the year is incomplete

    if temp_days >= config.MIN_DAYS_PER_YEAR:
        last_spring, first_fall = freeze_season(year_df)
        out.update({
            "tavg_f": year_df["tavg_f"].mean(),
            "tmax_f": year_df["tmax_f"].mean(),
            "tmin_f": year_df["tmin_f"].mean(),
            "hot_days": (year_df["tmax_f"] >= config.HOT_DAY_F).sum(),
            "warm_nights": (year_df["tmin_f"] >= config.WARM_NIGHT_F).sum(),
            "freeze_days": (year_df["tmin_f"] <= config.FREEZE_F).sum(),
            "last_spring_freeze_doy": last_spring,
            "first_fall_freeze_doy": first_fall,
            "freeze_free_days": first_fall - last_spring - 1,
        })

    if rain_days >= config.MIN_DAYS_PER_YEAR:
        rain = year_df["prcp_in"]
        total = rain.sum()
        out.update({
            "rain_total_in": total,
            "wet_days": (rain >= config.WET_DAY_IN).sum(),
            "heavy_rain_days": (rain >= config.HEAVY_RAIN_IN).sum(),
            "max_1day_rain_in": rain.max(),
            "pct_rain_from_1in_days": 100 * rain[rain >= 1.0].sum() / total if total else np.nan,
            # a missing day breaks a dry spell (we do not assume it was dry)
            "longest_dry_spell": longest_run((rain < config.WET_DAY_IN).fillna(False)),
        })
    return out


def build_annual(daily):
    rows = []
    for (station, city, region, year), year_df in daily.groupby(
            ["station", "city", "region", "year"]):
        row = {"station": station, "city": city, "region": region, "year": year}
        row.update(year_metrics(year_df))
        rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main():
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    frames, quality_rows = [], []
    for station_id in config.STATIONS:
        df, quality = clean_station(station_id)
        frames.append(df)
        quality_rows.append(quality)
    daily = pd.concat(frames, ignore_index=True)

    daily.to_csv(config.PROCESSED_DIR / "daily_clean.csv", index=False,
                 float_format="%.2f")
    quality = pd.DataFrame(quality_rows)
    annual = build_annual(daily)

    # how many usable years each station has
    usable = annual.groupby("station")[["tavg_f", "rain_total_in"]].count()
    quality["usable_temp_years"] = quality["station"].map(usable["tavg_f"])
    quality["usable_rain_years"] = quality["station"].map(usable["rain_total_in"])

    annual.to_csv(config.PROCESSED_DIR / "annual_metrics.csv", index=False,
                  float_format="%.3f")
    quality.to_csv(config.RESULTS_DIR / "data_quality.csv", index=False)

    print(f"Cleaned {len(daily):,} station-days from {len(config.STATIONS)} stations "
          f"({config.START_YEAR}-{config.END_YEAR}).")
    print(quality[["city", "days_in_file", "pct_missing_temp", "pct_missing_rain",
                   "usable_temp_years", "usable_rain_years"]].to_string(index=False))
    return daily, annual


if __name__ == "__main__":
    main()
