#!/usr/bin/env python3
"""Deterministic build of a per-county dekadal NDVI / vegetation-anomaly
series from WFP VAM (MODIS 6.1) for the ENSO Explorer.

Source: WFP VAM "Kenya: NDVI at Subnational Level" (HDX, CC-BY). The file
is on the OCHA legacy sub-county grid: admin2 p-codes are KE + county
(001-047) + subunit, so the county is exactly the 5-char p-code prefix.
No LLM/transcription: p-code prefix -> county, pixel-weighted rollup of
the WFP per-admin2 NDVI, county name from the OCHA COD admin1 table.

vim      = mean NDVI over the unit's pixels for the dekad
vim_avg  = long-term mean NDVI for that dekad-of-year (WFP baseline)
viq      = vim / vim_avg * 100  -> % of normal (the drought/pasture anomaly)

County rollup is pixel-weighted (n_pixels) so a county's value is the
true area-mean of its sub-units, not an unweighted average of them. viq
is recomputed from the rolled-up vim / vim_avg (never averaged directly).
"""
import csv
import sys
import openpyxl
import pyarrow as pa
import pyarrow.parquet as pq

NDVI = sys.argv[1]
COD_XLSX = sys.argv[2]
COUNTY_KEY = sys.argv[3]
OUT = sys.argv[4]


def norm(s):
    return s.lower().replace("-", " ").replace("'", "").strip()


# OCHA COD admin1: p-code -> county name (tier-1, not transcribed)
wb = openpyxl.load_workbook(COD_XLSX, read_only=True)
pcode_name = {r[4]: r[0] for r in list(wb["ken_admin1"].iter_rows(values_only=True))[1:]}

# canonical county -> gaul1_code, matched by normalized name
ck_rows = pq.read_table(COUNTY_KEY).to_pylist()
gaul_by_norm = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in ck_rows}

# accumulate pixel-weighted sums per (date, county p-code)
acc = {}
with open(NDVI, newline="") as f:
    for r in csv.DictReader(f):
        if r["adm_level"] != "2":
            continue
        cpc = r["PCODE"][:5]  # KE + county(001-047)
        try:
            npx = float(r["n_pixels"]); vim = float(r["vim"]); vavg = float(r["vim_avg"])
        except (ValueError, TypeError):
            continue  # skip blank/non-numeric cells (never guessed)
        k = (r["date"], cpc)
        a = acc.setdefault(k, {"npx": 0.0, "vim_w": 0.0, "vavg_w": 0.0})
        a["npx"] += npx
        a["vim_w"] += vim * npx
        a["vavg_w"] += vavg * npx

out = []
unmatched = set()
for (date, cpc), a in acc.items():
    name = pcode_name.get(cpc)
    if name is None or norm(name) not in gaul_by_norm:
        unmatched.add(cpc)
        continue
    county, gaul1_code = gaul_by_norm[norm(name)]
    if a["npx"] == 0 or a["vavg_w"] == 0:
        continue
    vim = a["vim_w"] / a["npx"]
    vavg = a["vavg_w"] / a["npx"]
    out.append({
        "county": county,
        "gaul1_code": gaul1_code,
        "date": date,
        "year": int(date[:4]),
        "month": int(date[5:7]),
        "ndvi": round(vim, 5),
        "ndvi_mean": round(vavg, 5),
        "ndvi_pct_normal": round(vim / vavg * 100, 3),
        "n_pixels": int(a["npx"]),
    })

if unmatched:
    print("UNMATCHED county p-codes (dropped):", sorted(unmatched))
out.sort(key=lambda d: (d["county"], d["date"]))
counties = sorted(set(r["county"] for r in out))
print(f"rows={len(out)} counties={len(counties)} dates={len(set(r['date'] for r in out))}")
print("date range:", out[0]["date"], "->", max(r["date"] for r in out))
vq = [r["ndvi_pct_normal"] for r in out]
print(f"pct_normal range: {min(vq):.1f} .. {max(vq):.1f}")

schema = pa.schema([
    ("county", pa.string()), ("gaul1_code", pa.float64()), ("date", pa.string()),
    ("year", pa.int32()), ("month", pa.int32()),
    ("ndvi", pa.float64()), ("ndvi_mean", pa.float64()),
    ("ndvi_pct_normal", pa.float64()), ("n_pixels", pa.int32()),
])
pq.write_table(pa.Table.from_pylist(out, schema=schema), OUT)
print("wrote", OUT)
