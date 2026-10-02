#!/usr/bin/env python3
"""Deterministic build of the ENSO/IOD driver indices for the KE-ENSO Block-5 outlook.

Pulls observed climate-DRIVER indices from PRIMARY sources (no model types a number):
  * RONI  - NOAA CPC Relative Oceanic Nino Index (seasonal, 3-mo running).  ENSO headline
            (the same index IWMI's dashboard leads with).
  * SOI   - NOAA CPC Southern Oscillation Index, STANDARDIZED block (monthly).
  * DMI   - NOAA PSL Dipole Mode Index (IOD), HadISST1.1 (monthly).

Emits two tidy long parquets under data/KE-enso-explorer/:
  * enso_drivers_monthly.parquet  [index, year, month, value]      (SOI, DMI)  -> time-series toggle
  * enso_drivers_seasonal.parquet [index, season, year, value]     (RONI native + SOI/DMI 3-mo means)
                                                                   -> analogue matching + MAM/OND

D11/D14: these are the ENSO/IOD *driver* indices (global, observed) -> allowed. Kenya rainfall
forecast stays Kenya-Met-only. All values parsed from the source text; none typed by a model.

Usage:  python3.12 enso_drivers_build.py
"""
import io, sys, collections
import requests
import pyarrow as pa, pyarrow.parquet as pq

OUT_DIR = "data/KE-enso-explorer"
RONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
SOI_URL  = "https://www.cpc.ncep.noaa.gov/data/indices/soi"
DMI_URL  = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data"
MISSING  = {-999.9, -9999.0, -99.99, -9.99}

# 3-month overlapping seasons, labelled by the year the 2nd/3rd months fall in (NOAA convention).
SEASONS = {
    "DJF": [(12, -1), (1, 0), (2, 0)],
    "JFM": [(1, 0), (2, 0), (3, 0)],
    "FMA": [(2, 0), (3, 0), (4, 0)],
    "MAM": [(3, 0), (4, 0), (5, 0)],
    "AMJ": [(4, 0), (5, 0), (6, 0)],
    "MJJ": [(5, 0), (6, 0), (7, 0)],
    "JJA": [(6, 0), (7, 0), (8, 0)],
    "JAS": [(7, 0), (8, 0), (9, 0)],
    "ASO": [(8, 0), (9, 0), (10, 0)],
    "SON": [(9, 0), (10, 0), (11, 0)],
    "OND": [(10, 0), (11, 0), (12, 0)],
    "NDJ": [(11, 0), (12, 0), (1, 1)],
}


def _get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text


def parse_roni(txt):
    """RONI: 'SEAS  YR  ANOM' whitespace rows. -> [(season, year, value)]."""
    out = []
    for ln in txt.splitlines():
        p = ln.split()
        if len(p) != 3 or p[0] not in SEASONS:
            continue
        try:
            season, year, val = p[0], int(p[1]), float(p[2])
        except ValueError:
            continue
        if val in MISSING:
            continue
        out.append((season, year, val))
    return out


def parse_soi_standardized(txt):
    """CPC SOI, STANDARDIZED block only. Fixed-width: year[0:4] then 12 x 6-char months.
    -> {(year, month): value}."""
    lines = txt.splitlines()
    start = next(i for i, l in enumerate(lines) if "STANDARDIZED" in l.upper())
    out = {}
    for ln in lines[start + 1:]:
        if len(ln) < 4 or not ln[:4].strip().lstrip("-").isdigit():
            continue
        year = int(ln[:4])
        body = ln[4:]
        for m in range(12):
            chunk = body[m * 6:(m + 1) * 6].strip()
            if not chunk:
                continue
            try:
                v = float(chunk)
            except ValueError:
                continue
            if v in MISSING:
                continue
            out[(year, m + 1)] = v
    return out


def parse_dmi(txt):
    """PSL DMI: header 'startyr endyr', then 'YEAR m1..m12', trailing prose. -> {(year,month):value}."""
    lines = txt.splitlines()
    y0, y1 = (int(x) for x in lines[0].split()[:2])
    out = {}
    for ln in lines[1:]:
        p = ln.split()
        if len(p) < 13 or not p[0].lstrip("-").isdigit():
            continue
        year = int(p[0])
        if not (y0 <= year <= y1):
            continue
        for m in range(12):
            try:
                v = float(p[m + 1])
            except (ValueError, IndexError):
                continue
            if v in MISSING:
                continue
            out[(year, m + 1)] = v
    return out


def seasonalise(monthly, index_name):
    """{(year,month):value} -> [(index, season, year, mean)] for each fully-covered 3-mo season."""
    out = []
    years = {y for (y, _m) in monthly}
    for y in sorted(years):
        for season, months in SEASONS.items():
            vals = [monthly.get((y + off, m)) for (m, off) in months]
            if any(v is None for v in vals):
                continue
            out.append((index_name, season, y, sum(vals) / 3.0))
    return out


def write_parquet(rows, cols, path):
    arrs = list(zip(*rows)) if rows else [[] for _ in cols]
    table = pa.table({c: list(a) for c, a in zip(cols, arrs)})
    pq.write_table(table, path)
    return len(rows)


def main():
    roni = parse_roni(_get(RONI_URL))
    soi_m = parse_soi_standardized(_get(SOI_URL))
    dmi_m = parse_dmi(_get(DMI_URL))

    # monthly long: SOI, DMI
    monthly_rows = ([("SOI", y, m, v) for (y, m), v in sorted(soi_m.items())]
                    + [("DMI", y, m, v) for (y, m), v in sorted(dmi_m.items())])
    n_mon = write_parquet(monthly_rows, ["index", "year", "month", "value"],
                          f"{OUT_DIR}/enso_drivers_monthly.parquet")

    # seasonal long: RONI native + SOI/DMI 3-mo means
    seasonal_rows = ([("RONI", s, y, v) for (s, y, v) in roni]
                     + seasonalise(soi_m, "SOI") + seasonalise(dmi_m, "DMI"))
    seasonal_rows.sort(key=lambda r: (r[0], r[2], r[1]))
    n_sea = write_parquet(seasonal_rows, ["index", "season", "year", "value"],
                          f"{OUT_DIR}/enso_drivers_seasonal.parquet")

    # report
    def span(idx, rows, yi):
        ys = [r[yi] for r in rows if r[0] == idx]
        return f"{min(ys)}-{max(ys)}" if ys else "none"
    print(f"monthly  rows={n_mon}  SOI {span('SOI', monthly_rows, 1)}  DMI {span('DMI', monthly_rows, 1)}")
    print(f"seasonal rows={n_sea}  RONI {span('RONI', seasonal_rows, 2)}  "
          f"SOI {span('SOI', seasonal_rows, 2)}  DMI {span('DMI', seasonal_rows, 2)}")


if __name__ == "__main__":
    main()
