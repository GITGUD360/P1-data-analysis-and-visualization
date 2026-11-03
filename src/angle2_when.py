"""
angle2_when.py
--------------
ANGLE 2 - WHEN?  Is South Carolina warming more by day or by night,
and in which season?

Method
  * Separate trends for the daily HIGH (TMAX, afternoon) and the daily LOW
    (TMIN, night / early morning) at every station.
  * Split the year into the four meteorological seasons
    (Winter = Dec-Feb, Spring = Mar-May, Summer = Jun-Aug, Fall = Sep-Nov)
    and fit a trend for each season, for highs and lows, statewide.
    December is counted with the following winter (Dec 2000 -> winter 2001).
  * A season is only used if at least 80 of its ~90 days have data.

Figures
  fig07_day_vs_night_by_city.png - highs vs lows trend for every city
  fig08_warming_by_season.png    - statewide trend for each season
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
import utils

SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
           6: "Summer", 7: "Summer", 8: "Summer", 9: "Fall", 10: "Fall", 11: "Fall"}
SEASON_ORDER = ["Winter", "Spring", "Summer", "Fall"]
MIN_DAYS_PER_SEASON = 80


def day_night_table(annual, suspects):
    rows = []
    for station, (city, region) in config.STATIONS.items():
        df = annual[annual["station"] == station]
        high = utils.trend(df["year"], df["tmax_f"])
        low = utils.trend(df["year"], df["tmin_f"])
        rows.append({
            "city": city, "region": region, "suspect_station": station in suspects,
            "highs_f_per_decade": high["per_decade"], "highs_p": high["p_value"],
            "lows_f_per_decade": low["per_decade"], "lows_p": low["p_value"],
        })
    table = pd.DataFrame(rows)
    table["nights_minus_days"] = table["lows_f_per_decade"] - table["highs_f_per_decade"]
    return table


def seasonal_table(daily, suspects):
    d = daily[~daily["station"].isin(suspects)].copy()
    d["season"] = d["date"].dt.month.map(SEASONS)
    d["season_year"] = d["year"] + (d["date"].dt.month == 12).astype(int)
    d = d[(d["season_year"] > config.START_YEAR) & (d["season_year"] <= config.END_YEAR)]

    per_station = (d.groupby(["station", "season", "season_year"])
                    .agg(tmax_f=("tmax_f", "mean"), tmin_f=("tmin_f", "mean"),
                         days=("tavg_f", "count"))
                    .reset_index())
    per_station = per_station[per_station["days"] >= MIN_DAYS_PER_SEASON]

    # turn into anomalies so that a missing station-year does not bias the mean
    for col in ["tmax_f", "tmin_f"]:
        base = per_station[per_station["season_year"] <= config.BASELINE[1]] \
            .groupby(["station", "season"])[col].mean()
        key = list(zip(per_station["station"], per_station["season"]))
        per_station[f"{col}_anom"] = per_station[col].values - base.reindex(key).values

    statewide = (per_station.groupby(["season", "season_year"])
                 [["tmax_f_anom", "tmin_f_anom"]].mean().reset_index())
    rows = []
    for season in SEASON_ORDER:
        s = statewide[statewide["season"] == season]
        high = utils.trend(s["season_year"], s["tmax_f_anom"])
        low = utils.trend(s["season_year"], s["tmin_f_anom"])
        rows.append({"season": season,
                     "highs_f_per_decade": high["per_decade"], "highs_ci95": high["ci95_per_decade"],
                     "highs_p": high["p_value"],
                     "lows_f_per_decade": low["per_decade"], "lows_ci95": low["ci95_per_decade"],
                     "lows_p": low["p_value"]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def fig_day_night(table):
    t = table.sort_values(["suspect_station", "nights_minus_days"], ascending=[False, True])
    fig, ax = plt.subplots(figsize=(10, 6.2))
    for i, (_, row) in enumerate(t.iterrows()):
        faded = row["suspect_station"]
        ax.plot([row["highs_f_per_decade"], row["lows_f_per_decade"]], [i, i],
                color="#c9c8c3", lw=2.5, zorder=1)
        ax.scatter(row["highs_f_per_decade"], i, s=90, zorder=3, edgecolor="white", linewidth=1.5,
                   color="#c9c8c3" if faded else config.DAY_COLOR)
        ax.scatter(row["lows_f_per_decade"], i, s=90, zorder=3, edgecolor="white", linewidth=1.5,
                   color="#c9c8c3" if faded else config.NIGHT_COLOR)
    ax.set_yticks(range(len(t)))
    ax.set_yticklabels([c + ("  (suspect data)" if s else "")
                        for c, s in zip(t["city"], t["suspect_station"])])
    ax.axvline(0, color=config.INK_MUTED, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Warming rate, °F per decade (1966-2025)")

    # direct labels on the top row instead of a legend box
    top = t.iloc[-1]
    ax.annotate("Nights (daily low)", xy=(top["lows_f_per_decade"], len(t) - 1),
                xytext=(top["lows_f_per_decade"], len(t) - 0.35), ha="center",
                color=config.NIGHT_COLOR, fontweight="bold", fontsize=10)
    ax.annotate("Days (daily high)", xy=(top["highs_f_per_decade"], len(t) - 1),
                xytext=(top["highs_f_per_decade"], len(t) - 0.35), ha="center",
                color=config.DAY_COLOR, fontweight="bold", fontsize=10)
    ax.set_ylim(-0.6, len(t) - 0.1)

    trusted = table[~table["suspect_station"]]
    biggest = trusted.sort_values("nights_minus_days", ascending=False)["city"].iloc[:2]
    ax.set_title(f"Nights warm fastest in the big cities: {biggest.iloc[0]} and "
                 f"{biggest.iloc[1].split(' (')[0]}")
    utils.subtitle(ax, f"Average of 9 trusted stations: nights +{trusted['lows_f_per_decade'].mean():.2f}"
                       f" °F/decade vs. days +{trusted['highs_f_per_decade'].mean():.2f}. "
                       "Sorted by how much faster nights warm.")
    utils.save(fig, "fig07_day_vs_night_by_city")


def fig_seasons(seasons):
    fig, ax = plt.subplots(figsize=(11, 5.6))
    x = np.arange(len(seasons))
    width = 0.36
    for offset, col, color, label in [(-width / 2, "highs", config.DAY_COLOR, "Days (daily high)"),
                                      (width / 2, "lows", config.NIGHT_COLOR, "Nights (daily low)")]:
        values = seasons[f"{col}_f_per_decade"]
        ax.bar(x + offset, values, width=width - 0.03, color=color, label=label)
        ax.errorbar(x + offset, values, yerr=seasons[f"{col}_ci95"], fmt="none",
                    ecolor=config.INK_2, capsize=3, lw=1)
        for xi, v, p, ci in zip(x + offset, values, seasons[f"{col}_p"], seasons[f"{col}_ci95"]):
            ax.text(xi, v + ci + 0.025, f"{v:+.2f}{utils.stars(p)}", ha="center", va="bottom",
                    fontsize=10, color=config.INK)
    ax.set_xticks(x)
    ax.set_xticklabels(seasons["season"], fontsize=12)
    ax.axhline(0, color=config.INK_MUTED, lw=0.8)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Warming rate, °F per decade")
    ax.legend(loc="upper right")
    winter = seasons.set_index("season").loc["Winter"]
    others = seasons[seasons["season"] != "Winter"][["highs_f_per_decade",
                                                     "lows_f_per_decade"]].values.mean()
    ratio = winter[["highs_f_per_decade", "lows_f_per_decade"]].mean() / others
    ax.set_title(f"Winter is warming {ratio:.1f}× faster than the rest of the year")
    utils.subtitle(ax, "Statewide trend per season, 9 trusted stations, 1966-2025.  Error bars = 95% "
                       "confidence interval.  * p<0.05  ** p<0.01  *** p<0.001")
    utils.save(fig, "fig08_warming_by_season")
    return ratio


# ---------------------------------------------------------------------------
def main():
    utils.set_style()
    annual = utils.load_annual()
    daily = utils.load_daily()
    suspects = utils.suspect_stations()

    table = day_night_table(annual, suspects)
    seasons = seasonal_table(daily, suspects)
    table.round(3).to_csv(config.RESULTS_DIR / "angle2_day_vs_night_by_city.csv", index=False)
    seasons.round(3).to_csv(config.RESULTS_DIR / "angle2_warming_by_season.csv", index=False)

    fig_day_night(table)
    ratio = fig_seasons(seasons)

    trusted = table[~table["suspect_station"]]
    print(table.round(2).to_string(index=False))
    print(seasons.round(3).to_string(index=False))
    return {
        "avg_highs_f_per_decade": trusted["highs_f_per_decade"].mean(),
        "avg_lows_f_per_decade": trusted["lows_f_per_decade"].mean(),
        "cities_nights_faster": int((trusted["nights_minus_days"] > 0).sum()),
        "n_trusted": len(trusted),
        "winter_vs_rest_ratio": ratio,
    }


if __name__ == "__main__":
    for key, value in main().items():
        print(f"{key}: {value}")
