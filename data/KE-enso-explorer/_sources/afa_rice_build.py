#!/usr/bin/env python3
"""Fold AFA Rice into the produce set.

Rice is the one crop the Agriculture & Food Authority (AFA) reports that the KNBS
NAPR county tables do not carry. Every other AFA crop is identical to the KNBS
NAPR (233/234 maize county-years matched exactly — AFA production is folded into
the NAPR), so only Rice is kept. Output matches the KNBS parquet schema so the
notebook can UNION it into the produce queries; source tagged 'AFA'.

Usage:  python3.12 afa_rice_build.py
"""
import pyarrow as pa, pyarrow.parquet as pq

OUT = "data/KE-enso-explorer"


def main():
    import pandas as pd
    afa = pq.read_table(f"{OUT}/afa_production.parquet").to_pandas()
    ck = pq.read_table(f"{OUT}/county_key.parquet").to_pandas()
    norm = lambda s: str(s).lower().replace("-", " ").replace("'", "").strip()
    gaul = {norm(r.county): r.gaul1_code for _, r in ck.iterrows()}

    r = afa[(afa.Crop == "Rice") & (afa.Year.str.match(r"^\d{4}$"))].copy()
    r["year"] = r.Year.astype(int)
    prod = r[r.Metric == "Production"].set_index(["County", "year"])["Value"]
    area = r[r.Metric == "Area"].set_index(["County", "year"])["Value"]

    rows = []
    for (county, year), pt in prod.items():
        rows.append({
            "crop": "Rice", "county": county,
            "gaul1_code": gaul.get(norm(county)),
            "year": int(year),
            "area_ha": float(area.get((county, year))) if (county, year) in area.index else None,
            "production_t": float(pt),
            "value_ksh": None,
            "source_file": "AFA (Agriculture & Food Authority)",
            "pdf_page": None, "dual_ok": None,
        })
    df = pd.DataFrame(rows).sort_values(["county", "year"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), f"{OUT}/afa_rice.parquet")
    print(f"rice rows={len(df)} counties={df.county.nunique()} "
          f"years={df.year.min()}-{df.year.max()} gaul-matched={df.gaul1_code.notna().sum()}/{len(df)}")


if __name__ == "__main__":
    main()
