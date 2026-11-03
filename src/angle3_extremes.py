"""
angle3_extremes.py
------------------
ANGLE 3 - WHAT DO PEOPLE FEEL?  Are extreme days becoming more common?

Averages hide what matters in daily life. Here we count the days that
affect health, crops, energy bills and flooding:

  * hot days      - high of 95 F or more          (heat stress, A/C demand)
  * warm nights   - low of 75 F or more           (no relief at night, health risk)
  * freeze days   - low of 32 F or less           (crops, pests, heating)
  * freeze-free season - days between the last spring freeze and the
                         first fall freeze        (growing season)
  * heavy rain days - 2 inches of rain or more in one day   (flash flooding)
  * plus yearly rain total, wettest day and longest dry spell

For each one we compare 1966-1995 with 1996-2025 and test the 60-year trend.
Temperature counts use the 9 trusted stations. Sumter's thermometer problem
does not affect its rain gauge, so rain uses all 10 stations.

Figures
  fig09_hot_days_and_warm_nights.png
  fig10_freeze_season.png
  fig11_heavy_rain.png
  fig12_extremes_scorecard.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config
import utils

# metric column, nice name, unit, which stations, "good" direction of the label
METRICS = [
    ("hot_days", "Hot days (high ≥ 95 °F)", "days/yr", "temp"),
    ("warm_nights", "Warm nights (low ≥ 75 °F)", "days/yr", "temp"),
    ("freeze_days", "Freeze days (low ≤ 32 °F)", "days/yr", "temp"),
    ("freeze_free_days", "Freeze-free season", "days", "temp"),
    ("rain_total_in", "Yearly rain total", "inches", "rain"),
    ("heavy_rain_days", "Heavy rain days (≥ 2 in)", "days/yr", "rain"),
    ("max_1day_rain_in", "Wettest day of the year", "inches", "rain"),
    ("longest_dry_spell", "Longest dry spell", "days", "rain"),
]

# storm year: (label, x of the label, y of the label)
STORMS = {1979: ("Hurricane David", 1979, 5.5),
          2015: ("Oct 2015 \"1000-year\" flood", 2006.5, 5.5),
          2016: ("Hurricane Matthew", 2016, 4.95),
          2024: ("Debby & Helene", 2021.8, 5.5)}


def scorecard(annual, suspects):
    rows = []
    for column, name, unit, kind in METRICS:
        exclude = suspects if kind == "temp" else []
        series = utils.statewide(annual, column, exclude=exclude)
        df = series.reset_index()
        fit = utils.trend(df["year"], df[column])
        then = utils.period_mean(df, column, config.BASELINE)
        now = utils.period_mean(df, column, config.RECENT)
        rows.append({"metric": name, "column": column, "unit": unit,
                     "mean_1966_1995": then, "mean_1996_2025": now,
                     "change": now - then, "pct_change": 100 * (now - then) / then,
                     "trend_per_decade": fit["per_decade"], "p_value": fit["p_value"],
                     "significant": fit["p_value"] < 0.05})
    return pd.DataFrame(rows)


def city_then_now(annual, column):
    rows = []
    for station, (city, region) in config.STATIONS.items():
        df = annual[annual["station"] == station]
        rows.append({"city": city, "region": region, "station": station,
                     "then": utils.period_mean(df, column, config.BASELINE),
                     "now": utils.period_mean(df, column, config.RECENT)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def fig_hot_and_warm(annual, suspects):
    hot = city_then_now(annual, "hot_days")
    warm = city_then_now(annual, "warm_nights")
    hot = hot[~hot["station"].isin(suspects)]
    warm = warm[~warm["station"].isin(suspects)]
    order = warm.sort_values("now")["city"].tolist()

    fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    panels = [(axes[0], hot, config.DAY_COLOR, "Hot days (high ≥ 95 °F)"),
              (axes[1], warm, config.NIGHT_COLOR, "Warm nights (low ≥ 75 °F)")]
    for ax, df, color, name in panels:
        df = df.set_index("city").loc[order]
        y = np.arange(len(df))
        ax.hlines(y, df["then"], df["now"], color="#c9c8c3", lw=2.5, zorder=1)
        ax.scatter(df["then"], y, s=70, color="white", edgecolor=config.INK_MUTED,
                   linewidth=1.5, zorder=2, label="1966-1995")
        ax.scatter(df["now"], y, s=80, color=color, edgecolor="white", linewidth=1.2,
                   zorder=3, label="1996-2025")
        for yi, (then, now) in enumerate(zip(df["then"], df["now"])):
            ax.text(max(then, now) + 1.5, yi, f"{round(now - then):+d}".replace("+0", "±0"), va="center",
                    fontsize=9.5, color=config.INK)
        ax.set_yticks(y)
        ax.set_yticklabels(order)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Days per year (average)")
        ax.set_xlim(0, df[["then", "now"]].values.max() * 1.15)
        ax.set_title(name, fontsize=12.5, pad=8)
        ax.legend(loc="lower right")

    w = warm.set_index("city")
    fig.suptitle(f"Warm nights have jumped: Charleston downtown now gets "
                 f"{w.loc['Charleston (Downtown)', 'now']:.0f} a year "
                 f"(was {w.loc['Charleston (Downtown)', 'then']:.0f})",
                 x=0.01, y=1.04, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.01, 0.975, "Average number of days per year, 1966-1995 (open circle) vs. "
                          "1996-2025 (filled). Number = change in days per year.",
             fontsize=10.5, color=config.INK_2, ha="left", gid="subtitle")
    fig.tight_layout()
    utils.save(fig, "fig09_hot_days_and_warm_nights")


def fig_freeze(annual, suspects):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    panels = [(axes[0], "freeze_days", "Freeze days per year (low ≤ 32 °F)", "#2a78d6"),
              (axes[1], "freeze_free_days", "Freeze-free season length (days)", "#1baf7a")]
    texts = {}
    for ax, column, name, color in panels:
        s = utils.statewide(annual, column, exclude=suspects)
        fit = utils.trend(s.index, s.values)
        ax.plot(s.index, s.values, color=color, lw=1, alpha=0.5)
        ax.scatter(s.index, s.values, color=color, s=14, alpha=0.6)
        ax.plot(s.index, s.rolling(10, center=True, min_periods=6).mean(),
                color=color, lw=2.6, label="10-year average")
        ax.plot(s.index, fit["intercept"] + fit["slope"] * s.index, color=config.INK,
                lw=1.1, ls="--", label="Trend")
        ax.set_title(name, fontsize=12.5, pad=8)
        low, high = s.min(), s.max()
        ax.set_ylim(low - 0.05 * (high - low), high + 0.32 * (high - low))
        p_text = "p < 0.001" if fit["p_value"] < 0.001 else f"p = {fit['p_value']:.3f}"
        ax.text(0.02, 0.95, f"{fit['per_decade']:+.1f} days per decade\n({p_text})",
                transform=ax.transAxes, va="top", fontsize=10.5, fontweight="bold",
                color=config.INK)
        ax.set_xlim(config.START_YEAR - 1, config.END_YEAR + 1)
        texts[column] = fit["per_decade"] * 6
        ax.legend(loc="upper right")
    fig.suptitle(f"Winters are softer: about {abs(texts['freeze_days']):.0f} fewer freezing "
                 f"nights and a {texts['freeze_free_days']:.0f}-day longer growing season",
                 x=0.01, y=1.04, ha="left", fontsize=15, fontweight="bold")
    fig.text(0.01, 0.975, "Statewide average of 9 trusted stations, 1966-2025 "
                          "(change shown = straight-line trend over 60 years).",
             fontsize=10.5, color=config.INK_2, ha="left", gid="subtitle")
    fig.tight_layout()
    utils.save(fig, "fig10_freeze_season")


def fig_heavy_rain(annual):
    s = utils.statewide(annual, "heavy_rain_days")
    fit = utils.trend(s.index, s.values)
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.bar(s.index, s.values, color=config.RAIN_COLOR, width=0.75, alpha=0.85)
    ax.plot(s.index, s.rolling(10, center=True, min_periods=6).mean(), color=config.INK,
            lw=2.2, label="10-year average")
    for year, (name, x, y) in STORMS.items():
        if year in s.index:
            ax.annotate(name, xy=(year, s[year]), xytext=(x, y), ha="center", va="bottom",
                        fontsize=9.5, color=config.INK_2,
                        arrowprops=dict(arrowstyle="-", color=config.INK_MUTED, lw=0.7))
    ax.set_ylim(0, 7.2)
    ax.set_xlim(config.START_YEAR - 1, config.END_YEAR + 1)
    ax.set_ylabel("Heavy rain days (≥ 2 in) per station")
    ax.legend(loc="upper right")
    ax.text(0.01, 0.97, f"Trend: {fit['per_decade']:+.2f} days per decade\n"
                        f"p = {fit['p_value']:.2f}  →  not significant",
            transform=ax.transAxes, ha="left", va="top", fontsize=11, fontweight="bold")
    ax.set_title("Heavy rain: big storm years come and go, with no clear trend (yet)")
    utils.subtitle(ax, "Average number of days with 2+ inches of rain at the 10 stations. "
                       "The largest spikes are tropical storms and hurricanes.")
    utils.save(fig, "fig11_heavy_rain")
    return fit


def fig_scorecard(card):
    fig, ax = plt.subplots(figsize=(11, 6))
    card = card.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(card))
    colors = []
    for _, row in card.iterrows():
        if not row["significant"]:
            colors.append("#c9c8c3")
        elif row["column"] in ("freeze_days",):
            colors.append("#2a78d6")
        else:
            colors.append("#e34948")
    ax.barh(y, card["pct_change"], color=colors, height=0.6)
    for yi, (_, row) in enumerate(card.iterrows()):
        label = (f"{row['mean_1966_1995']:.1f} → {row['mean_1996_2025']:.1f} {row['unit']}"
                 f"  ({int(round(row['pct_change'])):+d}%){utils.stars(row['p_value'])}")
        ax.text(max(row["pct_change"], 0) + 2, yi, label, va="center", ha="left", fontsize=10)
    ax.set_yticks(y)
    ax.set_yticklabels(card["metric"])
    ax.axvline(0, color=config.INK_MUTED, lw=0.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlim(-30, 110)
    ax.set_xlabel("Change from 1966-1995 to 1996-2025 (%)")
    ax.axhline(3.5, color=config.GRID, lw=1.2)
    ax.text(109, 7.45, "TEMPERATURE", ha="right", fontsize=9, color=config.INK_MUTED,
            fontweight="bold")
    ax.text(109, 3.2, "RAIN", ha="right", fontsize=9, color=config.INK_MUTED, fontweight="bold")
    ax.set_title("Scorecard: temperature extremes changed clearly, rain did not")
    utils.subtitle(ax, "Statewide averages.  Coloured = significant 60-year trend (p < 0.05); "
                       "grey = could be natural ups and downs.")
    utils.save(fig, "fig12_extremes_scorecard")


# ---------------------------------------------------------------------------
def main():
    utils.set_style()
    annual = utils.load_annual()
    suspects = utils.suspect_stations()

    card = scorecard(annual, suspects)
    card.round(3).to_csv(config.RESULTS_DIR / "angle3_extremes_scorecard.csv", index=False)
    per_city = pd.concat([city_then_now(annual, c).assign(metric=c)
                          for c, *_ in METRICS], ignore_index=True)
    per_city.round(2).to_csv(config.RESULTS_DIR / "angle3_extremes_by_city.csv", index=False)

    fig_hot_and_warm(annual, suspects)
    fig_freeze(annual, suspects)
    rain_fit = fig_heavy_rain(annual)
    fig_scorecard(card)

    print(card.round(3).to_string(index=False))
    findings = {r["column"]: (r["mean_1966_1995"], r["mean_1996_2025"], r["p_value"])
                for _, r in card.iterrows()}
    findings["heavy_rain_trend_p"] = rain_fit["p_value"]
    return findings


if __name__ == "__main__":
    for key, value in main().items():
        print(f"{key}: {value}")
