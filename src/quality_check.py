"""
quality_check.py
----------------
"Neighbour check" for station problems.

Weather stations get moved, re-sited or get new sensors. That can make a
station look like it suddenly warmed or cooled when the real climate did not.
Stations in the same state go up and down together from year to year, so we
compare every station with the average of all the other stations:

    difference = (station's anomaly) - (average anomaly of the other 9 stations)

If the 5-year running average of that difference ever drifts more than
3 F away from zero (healthy stations stay within about 2 F), the station is
flagged as "suspect" and is left out of the statewide averages (it is still
shown on the charts, clearly marked).

This script also draws the station map (Figure 1).
"""

import matplotlib.pyplot as plt
import pandas as pd

import config
import utils

DRIFT_LIMIT_F = 3.0

# where to put each city's name on the map so labels do not overlap (dx, dy)
LABEL_OFFSET = {
    "Charleston (Airport)": (-0.12, 0.10, "right"),
    "Charleston (Downtown)": (0.12, -0.10, "left"),
    "Beaufort": (-0.12, -0.06, "right"),
    "Columbia": (-0.12, 0.06, "right"),
    "Florence": (0.12, 0.0, "left"),
    "Sumter": (0.12, -0.06, "left"),
    "Greenville-Spartanburg": (0.0, 0.15, "center"),
    "Anderson": (-0.12, -0.04, "right"),
    "Clemson": (-0.12, 0.08, "right"),
    "Rock Hill": (0.12, 0.0, "left"),
}


def station_map():
    """Figure 1: where the 10 stations are, coloured by region."""
    quality = utils.load_quality()
    utils.set_style()
    fig, ax = plt.subplots(figsize=(8.6, 6.6))
    utils.draw_sc_outline(ax)
    for region in config.REGIONS:
        rows = quality[quality["region"] == region]
        ax.scatter(rows["lon"], rows["lat"], s=110, color=config.REGION_COLORS[region],
                   edgecolor="white", linewidth=2, zorder=3, label=region)
    for _, row in quality.iterrows():
        dx, dy, ha = LABEL_OFFSET[row["city"]]
        ax.text(row["lon"] + dx, row["lat"] + dy,
                f"{row['city']}\n{row['usable_temp_years']} years",
                fontsize=9.5, ha=ha, va="center", color=config.INK, zorder=4)
    ax.legend(loc="upper right", title="Region", title_fontsize=10, markerscale=1.1)
    ax.set_title("10 weather stations, 3 regions, 60 years of data")
    utils.subtitle(ax, "Number under each city = complete years of data "
                       "(330+ days) between 1966 and 2025.")
    utils.save(fig, "fig01_station_map")


def main():
    station_map()
    annual = utils.load_annual()
    for column in ["tavg_f", "tmax_f", "tmin_f"]:
        annual[f"{column}_anom"] = utils.add_anomaly(annual, column)

    rows, diffs = [], {}
    for station, (city, region) in config.STATIONS.items():
        worst = 0.0
        for column in ["tavg_f_anom", "tmax_f_anom", "tmin_f_anom"]:
            mine = annual[annual["station"] == station].set_index("year")[column]
            others = annual[annual["station"] != station].groupby("year")[column].mean()
            diff = (mine - others).rolling(5, center=True, min_periods=3).mean()
            worst = max(worst, diff.abs().max())
            if column == "tmax_f_anom":
                diffs[city] = diff
        rows.append({"station": station, "city": city, "region": region,
                     "max_5yr_drift_f": round(worst, 2),
                     "suspect": bool(worst > DRIFT_LIMIT_F)})

    check = pd.DataFrame(rows)
    check.to_csv(config.RESULTS_DIR / "neighbor_check.csv", index=False)
    print(check.to_string(index=False))

    # ---- figure: daytime-high difference from the neighbours ------------
    utils.set_style()
    fig, ax = plt.subplots(figsize=(10, 5))
    suspects = check.loc[check["suspect"], "city"].tolist()
    for city, diff in diffs.items():
        if city in suspects:
            continue
        ax.plot(diff.index, diff.values, color="#c9c8c3", lw=1.2)
    for city in suspects:
        diff = diffs[city]
        ax.plot(diff.index, diff.values, color="#e34948", lw=2.2)
        low_year = diff.idxmin()
        ax.annotate(f"{city}: daytime highs suddenly read\n"
                    f"{abs(diff.min()):.1f} °F colder than its neighbours",
                    xy=(low_year, diff.min()), xytext=(low_year - 30, diff.min() + 0.3),
                    fontsize=10, color=config.INK,
                    arrowprops=dict(arrowstyle="-", color=config.INK_MUTED, lw=0.8))
    ax.axhspan(-DRIFT_LIMIT_F, DRIFT_LIMIT_F, color="#f4f3f0", zorder=0)
    ax.axhline(0, color=config.INK_MUTED, lw=0.8)
    ax.text(1967, DRIFT_LIMIT_F - 0.1, "normal range (within 3 °F)", fontsize=9,
            color=config.INK_2, va="top")
    ax.set_xlim(config.START_YEAR, config.END_YEAR)
    ax.set_ylabel("Station minus neighbours (°F, 5-yr average)")
    ax.set_title("Data check: one station does not agree with its neighbours")
    utils.subtitle(ax, "Each grey line is a station that tracks the others well. "
                       "Red = flagged and left out of statewide averages.")
    utils.save(fig, "fig02_data_quality_check")
    return check


if __name__ == "__main__":
    main()
