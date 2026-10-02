#!/usr/bin/env python3
"""Build harveststat_county_production.parquet — Kenya subset of HarvestStat Africa.

Source: HarvestStat Africa v1.2 (Lee et al. 2025, Sci Data 10.1038/s41597-025-05001-z),
MIT-licensed, fetched straight from the release tag on GitHub — no OneDrive input
(git-full reproducibility).

Provenance chain: Kenya county agriculture offices -> Ministry of Agriculture &
Livestock Development -> FEWS NET Data Warehouse (FDW) -> HarvestStat harmonization
(boundary vintages KE1982A2/KE1989A2/KE2009A2 remapped onto the KE2013A1 47-county
frame via production-based ratios; 1989 districts are ~1:1 with modern counties).

What this script does (deterministic, no numbers touched):
  1. Download the pinned v1.2 CSV.
  2. Filter to Kenya; drop constant columns (admin_2='none', cps='All (PS)').
  3. Normalize county names to the repo's county_key.parquet spelling and join
     gaul1_code. Gate: all 47 counties must match, else abort.
  4. Rename to repo conventions (area_ha, production_t, yield_t_ha, crop, season).
  5. Write parquet next to the other served datasets.

Usage:  python3 harveststat_build.py        (needs pandas + pyarrow)
"""
import io
import sys
import urllib.request
from pathlib import Path

import pandas as pd

SRC_URL = ("https://raw.githubusercontent.com/HarvestStat/HarvestStat-Africa/"
           "v1.2/public/hvstat_africa_data_v1.2.csv")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "harveststat_county_production.parquet"
COUNTY_KEY = HERE.parent / "county_key.parquet"

# HarvestStat admin_1 spelling -> county_key spelling (all others identical)
COUNTY_RENAME = {"Elgeyo-Marakwet": "Elgeyo Marakwet"}


def main():
    print(f"fetching {SRC_URL} …")
    raw = urllib.request.urlopen(SRC_URL, timeout=120).read()
    df = pd.read_csv(io.BytesIO(raw))

    ke = df[df["country"] == "Kenya"].copy()
    n_src = len(ke)

    # constant-column sanity (schema drift guard for future versions)
    assert set(ke["admin_2"].unique()) == {"none"}, "Kenya gained admin_2 rows — revisit"
    assert set(ke["crop_production_system"].unique()) == {"All (PS)"}, \
        "Kenya gained crop-production-system splits — revisit"

    ke["county"] = ke["admin_1"].replace(COUNTY_RENAME)
    key = pd.read_parquet(COUNTY_KEY)
    ke = ke.merge(key, on="county", how="left", validate="many_to_one")
    unmatched = sorted(ke.loc[ke["gaul1_code"].isna(), "county"].unique())
    assert not unmatched, f"counties missing from county_key: {unmatched}"
    assert ke["county"].nunique() == 47, f"expected 47 counties, got {ke['county'].nunique()}"

    out = ke.rename(columns={
        "product": "crop",
        "season_name": "season",
        "area": "area_ha",
        "production": "production_t",
        "yield": "yield_t_ha",
    })[[
        "crop", "county", "gaul1_code", "season",
        "planting_year", "planting_month", "harvest_year", "harvest_month",
        "area_ha", "production_t", "yield_t_ha", "qc_flag", "fnid",
    ]].sort_values(["crop", "county", "season", "harvest_year"]).reset_index(drop=True)

    dup_keys = ["crop", "county", "season", "harvest_year"]
    dups = out.duplicated(dup_keys).sum()
    assert dups == 0, f"{dups} duplicate {dup_keys} rows"
    assert len(out) == n_src, "row count changed during processing"

    out.to_parquet(OUT, index=False)
    print(f"wrote {OUT}  ({len(out)} rows, {out['crop'].nunique()} crops, "
          f"{out['county'].nunique()} counties, "
          f"harvest years {out['harvest_year'].min()}–{out['harvest_year'].max()}, "
          f"seasons {sorted(out['season'].unique())})")


if __name__ == "__main__":
    sys.exit(main())
