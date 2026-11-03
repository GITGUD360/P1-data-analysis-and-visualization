"""
download_data.py
----------------
Task 1 - Download the data.

Downloads the daily weather record of each station in config.STATIONS from
NOAA NCEI (GHCN-Daily) and saves a trimmed copy in data/raw/.

The full NOAA files have ~100 columns (wind, snow depth, sunshine ...).
We only keep what this project needs: date, station info, rain (PRCP),
daily high (TMAX), daily low (TMIN) and their quality-flag columns.

The trimmed files are already included in the repo, so you only need to run
this if you want fresh data:

    python src/download_data.py
"""

import io
import sys
import urllib.request

import pandas as pd

import config

KEEP_COLUMNS = [
    "STATION", "DATE", "LATITUDE", "LONGITUDE", "ELEVATION", "NAME",
    "PRCP", "PRCP_ATTRIBUTES", "TMAX", "TMAX_ATTRIBUTES", "TMIN", "TMIN_ATTRIBUTES",
]


def download_station(station_id):
    """Download one station's CSV from NOAA and return it as a DataFrame."""
    url = config.NOAA_URL.format(station=station_id)
    print(f"  downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        text = response.read().decode("utf-8")
    return pd.read_csv(io.StringIO(text), low_memory=False)


def trim(df):
    """Keep only the columns and years we need (a few spare years at the start)."""
    df = df[[c for c in KEEP_COLUMNS if c in df.columns]].copy()
    year = pd.to_datetime(df["DATE"]).dt.year
    return df[(year >= config.START_YEAR - 6) & (year <= config.END_YEAR)]


def main():
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(config.STATIONS)} stations from NOAA NCEI ...")
    for station_id, (city, region) in config.STATIONS.items():
        try:
            df = trim(download_station(station_id))
        except Exception as err:  # network problems etc.
            print(f"  !! could not download {station_id} ({city}): {err}")
            sys.exit(1)
        out = config.RAW_DIR / f"{station_id}.csv"
        df.to_csv(out, index=False)
        print(f"  saved {out.name}: {city} ({region}), {len(df):,} days")
    print("Done.")


if __name__ == "__main__":
    main()
