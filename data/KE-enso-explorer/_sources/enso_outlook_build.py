#!/usr/bin/env python3
"""Analogue-outlook base for the KE-ENSO Block-5 figure (KE-09 layer 2).

Joins the observed ENSO/IOD driver state (enso_drivers_seasonal.parquet) to Kenya county
seasonal rainfall (chirps_county.parquet, variable=PTOT) and pre-computes, per target season
(MAM long rains, OND short rains) and county-year:
  * seasonal rainfall total, its 1991-2020 normal (mean/sd), anomaly %
  * tercile class vs the 1991-2020 distribution: Dry / Near / Wet
  * the PREDICTOR-window driver state (the lead signal available before the season):
        MAM <- DJF   |   OND <- JAS      (RONI, DMI, SOI)
  * the CONCURRENT-season driver state (RONI, DMI) for reference

The notebook then ranks analogue years by distance to the CURRENT predictor state (live, on the
small driver parquet) and shows what those years' rainfall did -> "next season likely what?".
Analogue = historical; the only forward element is the D14-allowed ENSO-state probability bar.

Baseline: 1991-2020 WMO normal. Terciles from that 30-yr distribution (33.3 / 66.7 pctile).
Deterministic; no number typed by a model. NOTE: admin1 includes 'Ilemi Triangle' (disputed
zone, not a county) -> flagged is_county=False.

Usage:  python3.12 enso_outlook_build.py
"""
import numpy as np
import pyarrow as pa, pyarrow.parquet as pq

OUT = "data/KE-enso-explorer"
CLIM0, CLIM1 = 1991, 2020
TARGETS = ["MAM", "OND"]
PREDICTOR = {"MAM": "DJF", "OND": "JAS"}   # lead window feeding each target season
NON_COUNTY = {"Ilemi Triangle"}


def load_drivers():
    d = pq.read_table(f"{OUT}/enso_drivers_seasonal.parquet").to_pandas()
    # {(index, season, year): value}
    return {(r["index"], r.season, r.year): r.value for _, r in d.iterrows()}


def main():
    import pandas as pd
    drv = load_drivers()
    ch = pq.read_table(f"{OUT}/chirps_county.parquet").to_pandas()
    ptot = ch[(ch.variable == "PTOT") & (ch.period.isin(TARGETS))].copy()

    rows = []
    for season in TARGETS:
        pred = PREDICTOR[season]
        sub = ptot[ptot.period == season]
        for county, g in sub.groupby("admin1_name", observed=True):
            g = g.dropna(subset=["value_mean"])
            gaul1 = int(g.gaul1_code.iloc[0]) if not g.gaul1_code.isna().all() else None
            clim = g[(g.year >= CLIM0) & (g.year <= CLIM1)]["value_mean"]
            if len(clim) < 20:            # need a real baseline
                continue
            cmean, csd = float(clim.mean()), float(clim.std(ddof=1))
            t1, t2 = np.percentile(clim, [100 / 3, 200 / 3])
            for _, r in g.iterrows():
                y, v = int(r.year), float(r.value_mean)
                tercile = "Dry" if v <= t1 else ("Wet" if v > t2 else "Near")
                rows.append({
                    "season": season, "year": y, "county": county, "gaul1_code": gaul1,
                    "is_county": county not in NON_COUNTY,
                    "ptot": round(v, 2), "clim_mean": round(cmean, 2), "clim_sd": round(csd, 2),
                    "anomaly_pct": round((v - cmean) / cmean * 100, 1) if cmean else None,
                    "tercile": tercile,
                    "roni_pred": drv.get(("RONI", pred, y)),
                    "dmi_pred":  drv.get(("DMI", pred, y)),
                    "soi_pred":  drv.get(("SOI", pred, y)),
                    "roni_conc": drv.get(("RONI", season, y)),
                    "dmi_conc":  drv.get(("DMI", season, y)),
                })
    df = pd.DataFrame(rows).sort_values(["season", "county", "year"]).reset_index(drop=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), f"{OUT}/enso_outlook_base.parquet")

    # report
    print(f"rows={len(df)}  counties={df.county.nunique()} (is_county={df[df.is_county].county.nunique()})")
    print(f"seasons={sorted(df.season.unique())}  years={df.year.min()}-{df.year.max()}")
    print("tercile split:", df.tercile.value_counts().to_dict())
    print("predictor coverage (non-null roni_pred / dmi_pred):",
          f"{df.roni_pred.notna().mean():.0%} / {df.dmi_pred.notna().mean():.0%}")
    # plausibility: strong El Nino + positive IOD OND years should skew Wet nationally
    for y in (1997, 2015, 2023):
        s = df[(df.season == "OND") & (df.year == y) & df.is_county]
        vc = s.tercile.value_counts()
        print(f"OND {y}: Wet={vc.get('Wet',0)} Near={vc.get('Near',0)} Dry={vc.get('Dry',0)}  "
              f"RONI_JAS={s.roni_pred.iloc[0] if len(s) else None}")
    for y in (2010, 2020):   # La Nina OND -> expect Dry-leaning
        s = df[(df.season == "OND") & (df.year == y) & df.is_county]
        vc = s.tercile.value_counts()
        print(f"OND {y}: Wet={vc.get('Wet',0)} Near={vc.get('Near',0)} Dry={vc.get('Dry',0)}  "
              f"RONI_JAS={s.roni_pred.iloc[0] if len(s) else None}")


if __name__ == "__main__":
    main()
