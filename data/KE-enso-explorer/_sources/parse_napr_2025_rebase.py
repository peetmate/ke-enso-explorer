#!/usr/bin/env python3
"""Rebase the 8 food crops' overlap years onto the 2025 NAPR edition, so
2020-2024 is single-edition (latest, incorporating KNBS's prior-year
revisions incl the sweet-potato 2022-23 change). 2019 stays from the 2024
edition (2025 doesn't cover it). Finger/pearl millet, coffee, cotton are
untouched (no comparable 2025 annex). De-rotated word extraction; 2024
provisional.
"""
import re, sys, collections
import fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF25, PARQUET = sys.argv[1], sys.argv[2]
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


def derot(doc, p):
    ws = doc[p].get_text("words")
    rows = collections.defaultdict(list)
    for w in ws:
        rows[round(w[0] / 8) * 8].append(w)
    return [[w[4] for w in sorted(rows[x], key=lambda w: -w[1])] for x in sorted(rows)]


def parse_crop(doc, pages):
    out = {}
    for p in pages:
        for toks in derot(doc, p):
            i = 0
            while i < len(toks) and re.fullmatch(r"[A-Za-z'./()-]+", toks[i]):
                i += 1
            name, nums = " ".join(toks[:i]).strip(), [num(t) for t in toks[i:] if num(t) is not None]
            if len(nums) >= 10 and re.match(r"^[A-Z][a-z]", name) and norm(name) not in ("county", "total", "kenya", "national"):
                out[name] = nums[:10]
    return out


doc = fitz.open(PDF25)
old = pq.read_table(PARQUET).to_pylist()
keymap = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in old}


def resolve(n):
    n = norm(n)
    if n in keymap:
        return keymap[n]
    hits = [v for k, v in keymap.items() if k.startswith(n + " ")]
    return hits[0] if len(hits) == 1 else None


rebased_crops = set(CROP_PAGES)
# keep everything EXCEPT the 8 crops' years 2020-2024 (those get replaced)
kept = [r for r in old if not (r["crop"] in rebased_crops and r["year"] in Y25)]
new = []
for crop, pages in CROP_PAGES.items():
    parsed = parse_crop(doc, pages)
    for name, v in parsed.items():
        r = resolve(name)
        if not r:
            continue
        cty, g = r
        for k, y in enumerate(Y25):
            new.append({"crop": crop, "county": cty, "gaul1_code": g, "year": y,
                        "area_ha": v[2 * k], "production_t": v[2 * k + 1], "value_ksh": None,
                        "source_file": "National-Agriculture-Production-Report-2025.pdf",
                        "pdf_page": pages[0] + 1, "dual_ok": True})
allrows = kept + new
schema = pq.read_table(PARQUET).schema
pq.write_table(pa.Table.from_pylist(allrows, schema=schema), PARQUET)
# report
byedition = collections.Counter(r["source_file"].split("-")[-1][:4] if "2025" in r["source_file"] else "2024ed" for r in allrows if r["crop"] in rebased_crops)
print(f"rebased {len(rebased_crops)} crops to 2025 for 2020-2024; +2019 from 2024ed.")
print(f"parquet {len(allrows)} rows; food-crop years {sorted(set(r['year'] for r in allrows if r['crop'] in rebased_crops))}")
sp = [r for r in allrows if r["crop"] == "Sweet potato" and r["county"] == "Homa Bay"]
print("Homa Bay sweet potato (rebased):", sorted((r["year"], r["production_t"]) for r in sp))
