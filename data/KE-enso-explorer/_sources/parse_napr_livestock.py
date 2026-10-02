#!/usr/bin/env python3
"""Dual-engine extraction of KNBS NAPR livestock-population annexes (clean,
not mirrored). Cattle/Sheep/Goats by county 2021-2023 (Annexes 15-17,
sub-types summed to species totals) + Camels/Donkeys (Annex 18). Head counts.
pdfplumber extract_tables vs PyMuPDF words, cell-by-cell; additivity vs the
printed Total row. No LLM-read values.
"""
import re, sys
import pdfplumber, fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF, COUNTY_KEY, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

# page(1-based) -> (year, species-list, col-count-after-county)
# Cattle/Sheep/Goats annex: County | c1 c2 (Cattle) | c3 c4 (Sheep) | c5 c6 (Goats)
CSG = {129: 2021}  # 2023 (p131) quarantined: dual-engine only 71%%
CAM = 132  # County | Donkeys | Camels | (beehives...)


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("\n", " ")).lower().replace("-", " ").replace("'", "").strip()


def num(s):
    if s is None:
        return None
    s = re.sub(r"[^\d.]", "", str(s).replace(",", ""))
    return float(s) if s not in ("", ".") else None


def is_county(s):
    return bool(s) and re.match(r"^[A-Z][A-Za-z' /-]+$", str(s).strip()) and norm(s) not in ("county", "")


def rows_pdfplumber(pdf, page1, ncols):
    pg = pdf.pages[page1 - 1]
    tbl = max(pg.extract_tables(), key=len)
    out, total = {}, None
    for r in tbl:
        if not r:
            continue
        c0 = re.sub(r"\s+", " ", str(r[0] or "").replace("\n", " ")).strip()
        vals = [num(x) for x in r[1:1 + ncols]]
        if c0.lower() in ("total", "kenya", "national"):
            total = vals
        elif is_county(r[0]):
            out[c0] = vals
    return out, total


def rows_pymupdf(page1, ncols):
    doc = fitz.open(PDF)
    words = doc[page1 - 1].get_text("words")
    rows = {}
    for w in words:
        rows.setdefault(round(w[1] / 3) * 3, []).append((w[0], w[4]))
    out = {}
    for y in rows:
        toks = [t for _, t in sorted(rows[y])]
        alpha, nm = [], []
        for t in toks:
            if re.match(r"^[A-Za-z'/-]+$", t) and not nm:
                alpha.append(t)
            elif re.match(r"^[\d,]+$", t) or t == "-":
                nm.append(num(t))
        name = " ".join(alpha).strip()
        if is_county(name) and len([x for x in nm if x is not None]) >= 2:
            out[name] = nm[:ncols]
    return out


def agreement(A, B):
    ag = tot = 0
    for c in A:
        bk = next((b for b in B if norm(b) == norm(c)), None)
        if not bk:
            continue
        for x, y in zip(A[c], (B[bk] + [None] * 12)):
            if x is None:
                continue
            tot += 1
            ag += int(y is not None and abs(x - y) < 0.5)
    return ag, tot


key = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in pq.read_table(COUNTY_KEY).to_pylist()}
pdf = pdfplumber.open(PDF)
out_rows = []

# Cattle/Sheep/Goats (6 value cols -> pairs summed to 3 species)
for page1, year in CSG.items():
    A, total = rows_pdfplumber(pdf, page1, 6)
    B = rows_pymupdf(page1, 6)
    ag, tot = agreement(A, B)
    # additivity per species (sum county pair vs total pair)
    add = "n/a"
    if total:
        sums = [sum(A[c][i] for c in A if A[c][i] is not None) for i in range(6)]
        add = [None if not total[i] else round(100 * sums[i] / total[i], 1) for i in range(6)]
    print(f"CSG {year} p{page1}: counties={len(A)} dual={ag}/{tot} additivity={add}")
    for c, v in A.items():
        k = key.get(norm(c))
        if not k or len(v) < 6:
            continue
        cty, g = k
        species = {"Cattle": (v[0] or 0) + (v[1] or 0), "Sheep": (v[2] or 0) + (v[3] or 0), "Goats": (v[4] or 0) + (v[5] or 0)}
        for sp, h in species.items():
            out_rows.append({"species": sp, "county": cty, "gaul1_code": g, "year": year, "head": h,
                             "source_file": "National-Agriculture-Production-Report-2024.pdf", "pdf_page": page1})

# Camels + Donkeys (Annex 18, year 2021): County | Donkeys | Camels | ...
Ac, totc = rows_pdfplumber(pdf, CAM, 2)
Bc = rows_pymupdf(CAM, 2)
agc, totc2 = agreement(Ac, Bc)
print(f"Donkeys/Camels 2021 p{CAM}: counties={len(Ac)} dual={agc}/{totc2}")
for c, v in Ac.items():
    k = key.get(norm(c))
    if not k or len(v) < 2:
        continue
    cty, g = k
    for sp, h in [("Donkeys", v[0]), ("Camels", v[1])]:
        if h is not None:
            out_rows.append({"species": sp, "county": cty, "gaul1_code": g, "year": 2021, "head": h,
                             "source_file": "National-Agriculture-Production-Report-2024.pdf", "pdf_page": CAM})

sch = pa.schema([("species", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                 ("year", pa.int32()), ("head", pa.float64()), ("source_file", pa.string()), ("pdf_page", pa.int32())])
pq.write_table(pa.Table.from_pylist(out_rows, schema=sch), OUT)
print("wrote", OUT, "rows:", len(out_rows), "species:", sorted(set(r["species"] for r in out_rows)),
      "years:", sorted(set(r["year"] for r in out_rows)), "counties:", len(set(r["county"] for r in out_rows)))
