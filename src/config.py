"""
config.py
---------
All the settings for the project live here so every script uses the same
stations, years, thresholds and folders.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Folders (everything is relative to the project root, so the repo works
# no matter where it is cloned)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
FIG_DIR = ROOT / "figures"
RESULTS_DIR = ROOT / "results"
BOUNDARY_FILE = ROOT / "data" / "sc_boundary.csv"

# ---------------------------------------------------------------------------
# Data source: NOAA NCEI Global Historical Climatology Network - Daily
# (the same data that powers https://www.ncei.noaa.gov/access/past-weather/)
# ---------------------------------------------------------------------------
NOAA_URL = ("https://www.ncei.noaa.gov/data/"
            "global-historical-climatology-network-daily/access/{station}.csv")

# 10 long-running weather stations, grouped into South Carolina's three
# well-known regions. Each one has at least 330 days of data in nearly every
# year from 1966 to 2025 (see results/data_quality.csv).
STATIONS = {
    # station id       city label               region
    "USW00013880": ("Charleston (Airport)",   "Coast"),
    "USW00013782": ("Charleston (Downtown)",  "Coast"),
    "USW00093831": ("Beaufort",               "Coast"),
    "USW00013883": ("Columbia",               "Midlands"),
    "USW00013744": ("Florence",               "Midlands"),
    "USC00388440": ("Sumter",                 "Midlands"),
    "USW00003870": ("Greenville-Spartanburg", "Upstate"),
    "USW00093846": ("Anderson",               "Upstate"),
    "USC00381770": ("Clemson",                "Upstate"),
    "USC00389350": ("Rock Hill",              "Upstate"),
}

REGIONS = ["Coast", "Midlands", "Upstate"]

# ---------------------------------------------------------------------------
# Study period: 60 years split into two 30-year "climate normal" periods
# ---------------------------------------------------------------------------
START_YEAR = 1966
END_YEAR = 2025
BASELINE = (1966, 1995)   # "then"
RECENT = (1996, 2025)     # "now"

# A year is only used if it has at least this many valid days
MIN_DAYS_PER_YEAR = 330

# ---------------------------------------------------------------------------
# Thresholds (in US units because that is what people in SC experience)
# ---------------------------------------------------------------------------
HOT_DAY_F = 95.0        # a "hot day": high temperature of 95 F or more
WARM_NIGHT_F = 75.0     # a "warm night": low temperature never drops below 75 F
FREEZE_F = 32.0         # freezing
HEAVY_RAIN_IN = 2.0     # a "heavy rain day": 2 inches or more in one day
WET_DAY_IN = 0.01       # a day counts as wet if it rains 0.01 inch or more

# ---------------------------------------------------------------------------
# Plot style (colors chosen to be color-blind safe)
# ---------------------------------------------------------------------------
REGION_COLORS = {"Coast": "#2a78d6", "Midlands": "#eb6834", "Upstate": "#1baf7a"}
DAY_COLOR = "#eb6834"    # daytime highs -> warm orange
NIGHT_COLOR = "#6250d6"  # night-time lows -> violet
RAIN_COLOR = "#2a78d6"
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8984"
GRID = "#e4e3df"
