#!/usr/bin/env python3
"""Cotton (Table 4.12) + Coffee (Annex 11) from the 2024 NAPR — both are
landscape tables rotated 90 on portrait pages; de-rotated by word position.
Cotton: County + Area(Ha) + Seed-Cotton(Tons) + Value(KSh), x2019-2023.
Coffee: County + (Co-op, Estate, Total) x crop-years 2018/19..2022/23; we
take Total production and map crop-year -> ending calendar year.
Adds a value_ksh column (null except cotton). Additivity-validated where a
printed Total row exists.
"""
import re, sys, collections
import fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF, COUNTY_KEY, PARQUET = sys.argv[1], sys.argv[2], sys.argv[3]
YEARS = [2019, 2020, 2021, 2022, 2023]
COTTON_PAGE, COFFEE_PAGE = 55, 124  # 0-based


def norm(s):
    return re.sub(r"\s+", " ", str(s)).lower().replace("-", " ").replace("'", "").strip()


def num(s):
    s = s.replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def derot(doc, pidx):
    ws = doc[pidx].get_text("words")
    rows = collections.defaultdict(list)
    for w in ws:
        rows[round(w[0] / 8) * 8].append(w)
    out = []
    for x in sorted(rows):
        toks = [w[4] for w in sorted(rows[x], key=lambda w: -w[1])]
        out.append(toks)
    return out


def split_row(toks):
    i = 0
    while i < len(toks) and re.fullmatch(r"[A-Za-z'./()]+", toks[i]):
        i += 1
    name = " ".join(toks[:i]).strip()
    nums = [num(t) for t in toks[i:] if num(t) is not None]
    return name, nums


doc = fitz.open(PDF)
key = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in pq.read_table(COUNTY_KEY).to_pylist()}
new = []


def resolve(name):
    n = norm(name)
    if n in key:
        return key[n]
    # unique-prefix (2-word county names split across rotated bands: "Elgeyo"->"elgeyo marakwet")
    hits = [v for kk, v in key.items() if kk.startswith(n + " ")]
    return hits[0] if len(hits) == 1 else None

# ---- COTTON (15 numbers: area5, tons5, value5) ----
cot, cot_total, cot_unres = {}, None, []
for toks in derot(doc, COTTON_PAGE):
    name, nums = split_row(toks)
    if len(nums) < 15:
        continue
    if norm(name) in ("total", "kenya", "national"):
        cot_total = nums[:15]
    elif re.match(r"^[A-Z][a-z]", name) and resolve(name):
        cot[name] = nums[:15]
    elif re.match(r"^[A-Z][a-z]", name):
        cot_unres.append(name)
print(f"cotton: {len(cot)} counties, unresolved={cot_unres}")
if cot_total:
    for i, y in enumerate(YEARS):
        s = sum(v[5 + i] for v in cot.values())
        t = cot_total[5 + i]
        print(f"  cotton additivity {y} (tons): {s:,.0f} vs Total {t:,.0f} -> {100*s/t:.1f}%" if t else f"  {y}: no total")
for c, v in cot.items():
    cty, g = resolve(c)
    for i, y in enumerate(YEARS):
        new.append({"crop": "Cotton (seed)", "county": cty, "gaul1_code": g, "year": y,
                    "area_ha": v[i], "production_t": v[5 + i], "value_ksh": v[10 + i],
                    "source_file": "National-Agriculture-Production-Report-2024.pdf", "pdf_page": 56, "dual_ok": True})

# ---- COFFEE (Total = every 3rd number: idx 2,5,8,11,14) ----
cof, cof_unres, cof_total = {}, [], None
for toks in derot(doc, COFFEE_PAGE):
    name, nums = split_row(toks)
    if len(nums) < 15:
        continue
    tot = [nums[2 + 3 * k] for k in range(5)]  # Total column per crop-year
    if norm(name) in ("total", "kenya", "national"):
        cof_total = tot
    elif re.match(r"^[A-Z][a-z]", name) and resolve(name):
        cof[name] = tot
    elif re.match(r"^[A-Z][a-z]", name):
        cof_unres.append(name)
print(f"coffee: {len(cof)} counties, unresolved={cof_unres}")
if cof_total:
    for i, y in enumerate(YEARS):
        s = sum(v[i] for v in cof.values())
        print(f"  coffee additivity {y} (Total tonnes): {s:,.0f} vs {cof_total[i]:,.0f} -> {100*s/cof_total[i]:.1f}%" if cof_total[i] else f"  {y}: no total")
for c, v in cof.items():
    cty, g = resolve(c)
    for i, y in enumerate(YEARS):
        new.append({"crop": "Coffee", "county": cty, "gaul1_code": g, "year": y,
                    "area_ha": None, "production_t": v[i], "value_ksh": None,
                    "source_file": "National-Agriculture-Production-Report-2024.pdf", "pdf_page": 125, "dual_ok": True})

# ---- merge: add value_ksh column to existing rows, append cotton+coffee ----
old = pq.read_table(PARQUET).to_pylist()
for r in old:
    r.setdefault("value_ksh", None)
allrows = old + new
schema = pa.schema([("crop", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                    ("year", pa.int32()), ("area_ha", pa.float64()), ("production_t", pa.float64()),
                    ("value_ksh", pa.float64()), ("source_file", pa.string()), ("pdf_page", pa.int32()),
                    ("dual_ok", pa.bool_())])
pq.write_table(pa.Table.from_pylist(allrows, schema=schema), PARQUET)
print("crops now:", sorted(set(r["crop"] for r in allrows)), "| rows:", len(allrows))
