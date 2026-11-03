"""
utils.py
--------
Small helpers shared by all the analysis scripts:
  * loading the processed data
  * fitting a straight-line trend (with a p-value)
  * one consistent Matplotlib style for every figure
"""

import sys

import matplotlib
matplotlib.use("Agg")  # draw to files, no window needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import config

# Windows terminals sometimes cannot print symbols like ° or ≥ - don't crash on them
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_annual():
    return pd.read_csv(config.PROCESSED_DIR / "annual_metrics.csv")


def load_daily():
    return pd.read_csv(config.PROCESSED_DIR / "daily_clean.csv", parse_dates=["date"])


def load_quality():
    return pd.read_csv(config.RESULTS_DIR / "data_quality.csv")


def suspect_stations():
    """Stations that failed the neighbor check in quality_check.py."""
    path = config.RESULTS_DIR / "neighbor_check.csv"
    if not path.exists():
        return []
    check = pd.read_csv(path)
    return check.loc[check["suspect"], "station"].tolist()


def city_order():
    """Cities in the order they appear in config (Coast -> Midlands -> Upstate)."""
    return [city for city, _ in config.STATIONS.values()]


def region_of(city):
    return {c: r for c, r in config.STATIONS.values()}[city]


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def trend(years, values):
    """
    Least-squares straight line through (year, value).
    Returns the change per decade, its 95% confidence interval, the p-value
    and the r-squared. Missing years are skipped.
    """
    years = np.asarray(years, dtype=float)
    values = np.asarray(values, dtype=float)
    ok = ~np.isnan(values)
    years, values = years[ok], values[ok]
    fit = stats.linregress(years, values)
    t_crit = stats.t.ppf(0.975, len(years) - 2)
    return {
        "per_decade": fit.slope * 10,
        "ci95_per_decade": t_crit * fit.stderr * 10,
        "p_value": fit.pvalue,
        "r_squared": fit.rvalue ** 2,
        "n_years": len(years),
        "intercept": fit.intercept,
        "slope": fit.slope,
    }


def period_mean(df, column, period):
    start, end = period
    return df.loc[(df["year"] >= start) & (df["year"] <= end), column].mean()


def add_anomaly(annual, column):
    """Difference from each station's own 1966-1995 average."""
    base = (annual[(annual["year"] >= config.BASELINE[0]) &
                   (annual["year"] <= config.BASELINE[1])]
            .groupby("station")[column].mean())
    return annual[column] - annual["station"].map(base)


def statewide(annual, column, exclude=()):
    """Average of all (trusted) stations for each year."""
    keep = annual[~annual["station"].isin(exclude)]
    return keep.groupby("year")[column].mean()


def stars(p):
    """Significance stars used in tables and charts."""
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


# ---------------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------------
def set_style():
    plt.rcParams.update({
        "figure.figsize": (10, 5.6),
        "figure.dpi": 100,
        "savefig.dpi": 200,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 15,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 26,
        "axes.labelsize": 11,
        "axes.labelcolor": config.INK_2,
        "axes.edgecolor": config.INK_MUTED,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": config.GRID,
        "grid.linewidth": 0.8,
        "xtick.color": config.INK_2,
        "ytick.color": config.INK_2,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.frameon": False,
        "legend.fontsize": 10,
        "lines.linewidth": 2,
        "text.color": config.INK,
    })


def subtitle(ax, text):
    """Gray one-line explanation under the title."""
    ax.text(0, 1.02, text, transform=ax.transAxes, fontsize=10.5,
            color=config.INK_2, va="bottom", ha="left", gid="subtitle")


def save(fig, name, source=True):
    """Save a figure into figures/ with the data source in the corner."""
    config.FIG_DIR.mkdir(parents=True, exist_ok=True)
    if source:
        fig.text(0.01, -0.01,
                 "Data: NOAA NCEI GHCN-Daily, 10 South Carolina stations, 1966-2025",
                 fontsize=8, color=config.INK_MUTED, ha="left", va="top", gid="source")
    path = config.FIG_DIR / f"{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.25)

    # A second copy for the slides: no big title, subtitle or source note (the slide
    # has its own), and 20% bigger text so it can be read from the back of a room
    if fig._suptitle is not None:
        fig._suptitle.set_visible(False)
    else:
        for ax in fig.axes:
            ax.set_title("")
    for artist in fig.findobj(lambda a: a.get_gid() in ("subtitle", "source")):
        artist.set_visible(False)
    for text in fig.findobj(plt.Text):
        text.set_fontsize(text.get_fontsize() * 1.2)
    slide_dir = config.FIG_DIR / "slides"
    slide_dir.mkdir(exist_ok=True)
    fig.savefig(slide_dir / f"{name}.png", bbox_inches="tight", pad_inches=0.15)

    plt.close(fig)
    print(f"  saved figures/{path.name}")
    return path


def draw_sc_outline(ax):
    """Draw the outline of South Carolina (lon/lat) as a light shape."""
    outline = pd.read_csv(config.BOUNDARY_FILE)
    ax.fill(outline["lon"], outline["lat"], color="#f4f3f0", zorder=0)
    ax.plot(outline["lon"], outline["lat"], color=config.INK_MUTED, lw=1, zorder=1)
    ax.set_aspect(1 / np.cos(np.radians(33.8)))  # keeps the state's real shape
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for side in ax.spines.values():
        side.set_visible(False)
