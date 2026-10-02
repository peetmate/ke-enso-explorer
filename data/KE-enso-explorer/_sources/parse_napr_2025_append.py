#!/usr/bin/env python3
"""Append 2024 (from the 2025 NAPR, de-rotated) to the 2019-2023 series, and
FLAG cross-edition differences in the overlap years 2020-2023 (KNBS revises
prior years). Keeps 2019-2023 from the 2024 edition as-is; adds year=2024
from the 2025 edition. Crops present + comparable in both editions only
(millet is combined in 2025 vs finger+pearl in 2024; cassava is new -> skipped).
"""
import re, sys, collections
import fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF25, PARQUET = sys.argv[1], sys.argv[2]
# 2025 crop -> 0-based page(s); mapped to our crop names
CROP_PAGES = {
    "Maize": [185, 186], "Sorghum": [188, 189], "Dry beans": [190, 191],
    "Cowpeas": [192], "Green grams": [193], "Pigeon peas": [194],
    "Irish potato": [195], "Sweet potato": [196, 197],
}
Y25 = [2020, 2021, 2022, 2023, 2024]


def norm(s):
    return re.sub(r"\s+", " ", str(s)).lower().replace("-", " ").replace("'", "").strip()


def num(s):
    s = s.replace(",", "").replace("*", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def derot(doc, pidx):
    ws = doc[pidx].get_text("words")
    rows = collections.defaultdict(list)
    for w in ws:
        rows[round(w[0] / 8) * 8].append(w)
    return [[w[4] for w in sorted(rows[x], key=lambda w: -w[1])] for x in sorted(rows)]


def parse_crop(doc, pages):
    out, total = {}, None
    for p in pages:
        for toks in derot(doc, p):
            i = 0
            while i < len(toks) and re.fullmatch(r"[A-Za-z'./()-]+", toks[i]):
                i += 1
            name = " ".join(toks[:i]).strip()
            nums = [num(t) for t in toks[i:] if num(t) is not None]
            if len(nums) < 10:
                continue
            if norm(name) in ("total", "kenya", "national"):
                total = nums[:10]
            elif re.match(r"^[A-Z][a-z]", name) and norm(name) != "county":
                out[name] = nums[:10]
    return out, total


doc = fitz.open(PDF25)
old = pq.read_table(PARQUET).to_pylist()
existing = {(r["crop"], norm(r["county"]), r["year"]): r["production_t"] for r in old}
keymap = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in old}  # county -> canonical/gaul from existing rows


def resolve(n):
    n = norm(n)
    if n in keymap:
        return keymap[n]
    hits = [v for k, v in keymap.items() if k.startswith(n + " ")]
    return hits[0] if len(hits) == 1 else None


new2024, diffs = [], []
for crop, pages in CROP_PAGES.items():
    parsed, total = parse_crop(doc, pages)
    # additivity for 2024 (prod = idx 9)
    add = None
    if total:
        s = sum(v[9] for v in parsed.values())
        add = f"{100*s/total[9]:.1f}%" if total[9] else "n/a"
    matched = 0
    for name, v in parsed.items():
        r = resolve(name)
        if not r:
            continue
        cty, g = r
        matched += 1
        # append 2024
        new2024.append({"crop": crop, "county": cty, "gaul1_code": g, "year": 2024,
                        "area_ha": v[8], "production_t": v[9], "value_ksh": None,
                        "source_file": "National-Agriculture-Production-Report-2025.pdf",
                        "pdf_page": pages[0] + 1, "dual_ok": True})
        # diff overlap 2020-2023 (prod) vs existing 2024-edition
        for k, y in enumerate(Y25[:4]):
            v25 = v[2 * k + 1]
            v24 = existing.get((crop, norm(cty), y))
            if v24 is not None and v25 is not None and abs(v25 - v24) > max(1.0, 0.005 * v24):
                diffs.append((crop, cty, y, v24, v25))
    print(f"{crop:14} 2025 counties={len(parsed):2} matched={matched:2} 2024-additivity={add}")

# report edition differences
print(f"\n=== cross-edition diffs (2020-2023 prod, |Δ|>0.5%): {len(diffs)} ===")
for d in diffs[:15]:
    print(f"  {d[0]} {d[1]} {d[2]}: 2024ed={d[3]:,.0f} -> 2025ed={d[4]:,.0f} (Δ{100*(d[4]-d[3])/d[3]:+.1f}%)")
if len(diffs) > 15:
    print(f"  ... +{len(diffs)-15} more")

# save the edition-diff report for provenance
import csv as _csv
dp = PARQUET.rsplit("/", 1)[0] + "/_sources/edition_diffs_2024ed_vs_2025ed.csv"
with open(dp, "w", newline="") as f:
    w = _csv.writer(f)
    w.writerow(["crop", "county", "year", "prod_2024edition", "prod_2025edition", "pct_change"])
    for d in diffs:
        w.writerow([d[0], d[1], d[2], round(d[3], 1), round(d[4], 1), round(100 * (d[4] - d[3]) / d[3], 2)])
print("wrote diff report:", dp)

# write: existing + 2024
allrows = old + new2024
schema = pq.read_table(PARQUET).schema
pq.write_table(pa.Table.from_pylist(allrows, schema=schema), PARQUET)
print(f"\nappended {len(new2024)} rows (year=2024, {len(set(r['crop'] for r in new2024))} crops); parquet now {len(allrows)} rows, years {sorted(set(r['year'] for r in allrows))}")
