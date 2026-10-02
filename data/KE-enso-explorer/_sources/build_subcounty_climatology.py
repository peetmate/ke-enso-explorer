#!/usr/bin/env python3
"""
build_subcounty_climatology.py

Calculates 1991–2020 WMO baseline seasonal rainfall climatology (MAM and OND)
for all 290 Kenyan IEBC subcounties using CHIRPS v3 observational rasters.
Outputs data/KE-enso-explorer/subcounty_rainfall_climatology.parquet
"""

import json
import os
import urllib.request
import numpy as np
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.mask import mask

DATA_DIR = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer"
TOPO_PATH = os.path.join(DATA_DIR, "ken_adm2_iebc_simple.topojson")
OUT_PARQUET = os.path.join(DATA_DIR, "subcounty_rainfall_climatology.parquet")
OUT_META = os.path.join(DATA_DIR, "subcounty_rainfall_climatology.meta.json")
SITE_OUT_PARQUET = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/_site/data/KE-enso-explorer/subcounty_rainfall_climatology.parquet"

MAM_TIF = "/tmp/chirps_clim/PTOT_MAM_1991-2020_mean.tif"
OND_TIF = "/tmp/chirps_clim/PTOT_OND_1991-2020_mean.tif"

def main():
    print("Loading subcounty geometries from:", TOPO_PATH)
    gdf = gpd.read_file(TOPO_PATH)
    print(f"Loaded {len(gdf)} subcounties.")

    # Open rasters
    with rasterio.open(MAM_TIF) as src_mam, rasterio.open(OND_TIF) as src_ond:
        records = []
        for idx, row in gdf.iterrows():
            geom = [row.geometry]
            # MAM
            try:
                img_mam, _ = mask(src_mam, geom, crop=True, nodata=np.nan, all_touched=True)
                val_mam = img_mam[~np.isnan(img_mam)]
                val_mam = val_mam[val_mam >= 0]
                mam_mean = float(np.nanmean(val_mam)) if len(val_mam) > 0 else 0.0
            except Exception as e:
                print(f"MAM error on {row['admin2_name']}: {e}")
                mam_mean = 0.0

            # OND
            try:
                img_ond, _ = mask(src_ond, geom, crop=True, nodata=np.nan, all_touched=True)
                val_ond = img_ond[~np.isnan(img_ond)]
                val_ond = val_ond[val_ond >= 0]
                ond_mean = float(np.nanmean(val_ond)) if len(val_ond) > 0 else 0.0
            except Exception as e:
                print(f"OND error on {row['admin2_name']}: {e}")
                ond_mean = 0.0

            tot = mam_mean + ond_mean
            mam_pct = (mam_mean / tot * 100.0) if tot > 0 else 50.0
            ond_pct = (ond_mean / tot * 100.0) if tot > 0 else 50.0

            records.append({
                "adm1_name": row["admin1_name"],
                "adm1_pcode": row["admin1_pcode"],
                "adm2_name": row["admin2_name"],
                "adm2_pcode": row["admin2_pcode"],
                "area_sqkm": float(row["area_sqkm"]) if row.get("area_sqkm") is not None else 0.0,
                "mam_mean_mm": round(mam_mean, 1),
                "ond_mean_mm": round(ond_mean, 1),
                "bimodal_total_mm": round(tot, 1),
                "mam_pct": round(mam_pct, 1),
                "ond_pct": round(ond_pct, 1),
                "dominant_season": "MAM (Long Rains)" if mam_mean >= ond_mean else "OND (Short Rains)"
            })

    df = pd.DataFrame(records)
    print(f"Computed climatology for {len(df)} subcounties. Sample:")
    print(df.head(10))

    # Save parquet
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"Saved: {OUT_PARQUET} ({os.path.getsize(OUT_PARQUET)} bytes)")

    if os.path.exists(os.path.dirname(SITE_OUT_PARQUET)):
        df.to_parquet(SITE_OUT_PARQUET, index=False)
        print(f"Copied to: {SITE_OUT_PARQUET}")

    # Metadata
    meta = {
        "dataset": "subcounty_rainfall_climatology",
        "description": "1991–2020 WMO baseline seasonal precipitation climatology (MAM and OND) per subcounty across Kenya",
        "source": "CHIRPS v3 (UCSB Climate Hazards Center) 0.05° observational rainfall gridded blending",
        "spatial_resolution": "IEBC 2019 Sub-county Boundaries (290 units)",
        "temporal_baseline": "1991–2020 WMO Climatological Normal",
        "columns": {
            "adm1_name": "County name",
            "adm1_pcode": "Official county pcode",
            "adm2_name": "Sub-county name",
            "adm2_pcode": "Official sub-county pcode",
            "area_sqkm": "Sub-county land area (km²)",
            "mam_mean_mm": "Long Rains (MAM) 1991-2020 climatological mean rainfall (mm)",
            "ond_mean_mm": "Short Rains (OND) 1991-2020 climatological mean rainfall (mm)",
            "bimodal_total_mm": "Combined bimodal rainfall total (MAM + OND mm)",
            "mam_pct": "Percentage share of bimodal total occurring during MAM (%)",
            "ond_pct": "Percentage share of bimodal total occurring during OND (%)",
            "dominant_season": "Dominant seasonal rainfall peak (MAM vs OND)"
        }
    }
    with open(OUT_META, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata to: {OUT_META}")

if __name__ == "__main__":
    main()
