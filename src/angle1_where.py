"""
angle1_where.py
---------------
ANGLE 1 - WHERE?  Which South Carolina city has warmed the most?

Method
  * For every station we take the yearly average temperature
    ((daily high + daily low) / 2, averaged over the year).
  * We fit a straight line through 1966-2025 -> warming rate in F per decade,
    with a 95% confidence interval and a p-value (is it more than noise?).
  * We also compare the two 30-year periods 1966-1995 and 1996-2025.
  * The statewide line is the average of the 9 trusted stations.

Figures
  fig03_statewide_warming.png   - SC as a whole, every year vs. the 1966-95 normal
  fig04_warming_rate_by_city.png - ranking of the 10 cities
  fig05_warming_map.png          - the same ranking on a map
  fig06_warming_stripes.png      - every city, every year, as coloured stripes
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

import config
import utils


def trend_table(annual, suspects):
    rows = []
    for station, (city, region) in config.STATIONS.items():
        df = annual[annual["station"] == station]
        fit = utils.trend(df["year"], df["tavg_f"])
        rows.append({
            "station": station, "city": city, "region": region,
            "warming_f_per_decade": fit["per_decade"],
            "ci95": fit["ci95_per_decade"],
            "p_value": fit["p_value"],
            "significant": fit["p_value"] < 0.05,
            "change_over_60yrs_f": fit["per_decade"] * 6,
            "mean_1966_1995_f": utils.period_mean(df, "tavg_f", config.BASELINE),
            "mean_1996_2025_f": utils.period_mean(df, "tavg_f", config.RECENT),
            "suspect_station": station in suspects,
        })
    table = pd.DataFrame(rows)
    table["period_change_f"] = table["mean_1996_2025_f"] - table["mean_1966_1995_f"]
    table = table.sort_values("warming_f_per_decade", ascending=False)
    table.insert(0, "rank", range(1, len(table) + 1))
    return table


# ---------------------------------------------------------------------------
def fig_statewide(annual, suspects):
    anomaly = utils.statewide(annual, "tavg_anom", exclude=suspects)
    fit = utils.trend(anomaly.index, anomaly.values)
    years = anomaly.index.values

    fig, ax = plt.subplots()
    colors = np.where(anomaly.values >= 0, "#e34948", "#2a78d6")
    ax.bar(years, anomaly.values, color=colors, width=0.8, alpha=0.85)
    smooth = anomaly.rolling(10, center=True, min_periods=6).mean()
    ax.plot(years, smooth.values, color=config.INK, lw=2.2, label="10-year average")
    ax.plot(years, fit["intercept"] + fit["slope"] * years, color=config.INK, lw=1.2,
            ls="--", label="Straight-line trend")
    ax.axhline(0, color=config.INK_MUTED, lw=0.8)
    hottest = anomaly.idxmax()
    ax.annotate(f"{hottest}: warmest single year (+{anomaly.max():.1f} °F)",
                xy=(hottest, anomaly.max()), xytext=(hottest + 2, anomaly.max() + 0.45),
                fontsize=10, va="center",
                arrowprops=dict(arrowstyle="-", color=config.INK_MUTED, lw=0.8))
    ax.text(2000, -0.75,
            f"Trend: +{fit['per_decade']:.2f} °F per decade\n"
            f"(± {fit['ci95_per_decade']:.2f}, p < 0.001)\n"
            f"≈ +{fit['per_decade'] * 6:.1f} °F over 60 years",
            fontsize=11, va="top", color=config.INK, fontweight="bold")
    ax.set_xlim(config.START_YEAR - 1, config.END_YEAR + 1)
    ax.set_ylim(-2.0, 3.8)
    ax.set_ylabel("Difference from 1966-1995 average (°F)")
    ax.legend(loc="upper left")
    ax.set_title(f"South Carolina has warmed about {fit['per_decade'] * 6:.0f} °F since the 1960s")
    utils.subtitle(ax, "Yearly average temperature of 9 trusted stations, compared with "
                       "the 1966-1995 normal. Red = warmer than normal.")
    utils.save(fig, "fig03_statewide_warming")

    # plain statewide "warming stripes" band used on the title slide
    band, ax = plt.subplots(figsize=(13.33, 1.4))
    ax.imshow([anomaly.values], aspect="auto", cmap="RdBu_r",
              norm=TwoSlopeNorm(vmin=-2.6, vcenter=0, vmax=2.6))
    ax.axis("off")
    band.savefig(config.FIG_DIR / "slides" / "title_stripes.png", bbox_inches="tight",
                 pad_inches=0, dpi=200)
    plt.close(band)
    return fit


def fig_ranking(table):
    t = table.sort_values("warming_f_per_decade")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(t))
    for i, (_, row) in enumerate(t.iterrows()):
        color = "#c9c8c3" if row["suspect_station"] else config.REGION_COLORS[row["region"]]
        ax.barh(i, row["warming_f_per_decade"], color=color, height=0.62)
        ax.errorbar(row["warming_f_per_decade"], i, xerr=row["ci95"], color=config.INK_2,
                    capsize=3, lw=1)
        label = f"{row['warming_f_per_decade']:+.2f}{utils.stars(row['p_value'])}"
        x = max(row["warming_f_per_decade"] + row["ci95"], 0) + 0.03
        ax.text(x, i, label, va="center", fontsize=10, color=config.INK)
    ax.set_yticks(y)
    ax.set_yticklabels([c + ("  (suspect data)" if s else "")
                        for c, s in zip(t["city"], t["suspect_station"])])
    ax.axvline(0, color=config.INK_MUTED, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Warming rate, °F per decade (1966-2025)   ·   bars show 95% confidence interval")
    handles = [plt.Rectangle((0, 0), 1, 1, color=config.REGION_COLORS[r]) for r in config.REGIONS]
    ax.set_xlim(-0.35, 1.0)
    ax.legend(handles, config.REGIONS, loc="lower right", title="Region")
    top = table.iloc[0]
    ax.set_title(f"{top['city']} warms fastest, but the top four cities are nearly tied")
    utils.subtitle(ax, "Straight-line trend of each city's yearly average temperature.  "
                       "* p<0.05   ** p<0.01   *** p<0.001")
    utils.save(fig, "fig04_warming_rate_by_city")


def fig_map(table):
    quality = utils.load_quality().set_index("city")
    fig, ax = plt.subplots(figsize=(8.6, 6.6))
    utils.draw_sc_outline(ax)
    trusted = table[~table["suspect_station"]]
    norm = plt.Normalize(0, trusted["warming_f_per_decade"].max())
    cmap = plt.get_cmap("OrRd")
    for _, row in table.iterrows():
        lon, lat = quality.loc[row["city"], ["lon", "lat"]]
        if row["suspect_station"]:
            ax.scatter(lon, lat, s=260, facecolor="white", edgecolor=config.INK_MUTED,
                       linewidth=1.5, zorder=3)
            text = f"{row['city']}\n(suspect data)"
        else:
            ax.scatter(lon, lat, s=80 + 600 * row["warming_f_per_decade"],
                       color=cmap(0.25 + 0.75 * norm(row["warming_f_per_decade"])),
                       edgecolor="white", linewidth=1.5, zorder=3)
            text = f"{row['city']}\n+{row['warming_f_per_decade']:.2f} °F/decade"
        dx, dy, ha = MAP_LABELS[row["city"]]
        ax.text(lon + dx, lat + dy, text, fontsize=9.5, ha=ha, va="center", zorder=4)
    ax.set_title("Every trusted station in the state is warming")
    utils.subtitle(ax, "Bigger, darker circle = faster warming (°F per decade, 1966-2025)")
    utils.save(fig, "fig05_warming_map")


MAP_LABELS = {
    "Charleston (Airport)": (-0.14, 0.10, "right"),
    "Charleston (Downtown)": (0.14, -0.12, "left"),
    "Beaufort": (-0.14, -0.06, "right"),
    "Columbia": (-0.16, 0.08, "right"),
    "Florence": (0.14, 0.0, "left"),
    "Sumter": (0.14, -0.08, "left"),
    "Greenville-Spartanburg": (0.0, 0.18, "center"),
    "Anderson": (-0.14, -0.06, "right"),
    "Clemson": (-0.14, 0.10, "right"),
    "Rock Hill": (0.14, -0.02, "left"),
}


def fig_stripes(annual, table):
    order = table.sort_values("warming_f_per_decade", ascending=False)["city"].tolist()
    grid = annual.pivot(index="city", columns="year", values="tavg_anom").loc[order]
    suspect = set(table.loc[table["suspect_station"], "city"])
    order = [c + "  (suspect data)" if c in suspect else c for c in order]
    fig, ax = plt.subplots(figsize=(11, 5.6))
    norm = TwoSlopeNorm(vmin=-3, vcenter=0, vmax=3)
    image = ax.imshow(grid.values, aspect="auto", cmap="RdBu_r", norm=norm,
                      extent=[grid.columns.min() - 0.5, grid.columns.max() + 0.5,
                              len(order) - 0.5, -0.5], interpolation="nearest")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order)
    ax.grid(False)
    for side in ax.spines.values():
        side.set_visible(False)
    bar = fig.colorbar(image, ax=ax, pad=0.015, fraction=0.03)
    bar.set_label("°F vs. the city's 1966-1995 average")
    bar.outline.set_visible(False)
    ax.set_title("Warming stripes: blue years fade, red years take over")
    utils.subtitle(ax, "Each square = one city in one year. Cities sorted from fastest "
                       "warming (top) to slowest. White = missing year.")
    utils.save(fig, "fig06_warming_stripes")


# ---------------------------------------------------------------------------
def main():
    utils.set_style()
    annual = utils.load_annual()
    annual["tavg_anom"] = utils.add_anomaly(annual, "tavg_f")
    suspects = utils.suspect_stations()

    table = trend_table(annual, suspects)
    table.round(3).to_csv(config.RESULTS_DIR / "angle1_warming_by_city.csv", index=False)

    state_fit = fig_statewide(annual, suspects)
    fig_ranking(table)
    fig_map(table)
    fig_stripes(annual, table)

    trusted = table[~table["suspect_station"]]
    region_avg = trusted.groupby("region")["warming_f_per_decade"].mean()
    findings = {
        "statewide_f_per_decade": state_fit["per_decade"],
        "statewide_ci95": state_fit["ci95_per_decade"],
        "statewide_p": state_fit["p_value"],
        "fastest_city": table.iloc[0]["city"],
        "fastest_rate": table.iloc[0]["warming_f_per_decade"],
        "slowest_trusted_city": trusted.iloc[-1]["city"],
        "slowest_trusted_rate": trusted.iloc[-1]["warming_f_per_decade"],
        "n_significant": int(trusted["significant"].sum()),
        "n_trusted": len(trusted),
        **{f"region_{r}": v for r, v in region_avg.items()},
    }
    print(table[["rank", "city", "warming_f_per_decade", "ci95", "p_value",
                 "period_change_f"]].round(3).to_string(index=False))
    return findings


if __name__ == "__main__":
    for key, value in main().items():
        print(f"{key}: {value}")
