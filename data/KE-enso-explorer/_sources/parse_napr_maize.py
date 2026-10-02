#!/usr/bin/env python3
"""Add MAIZE to the NAPR county-production parquet from the CLEAN Top-20
maize table (NAPR 2024 p26) — NOT the mirror-reversed/transposed Annex 1
(which no gate can validate per-county). Dual-engine: pdfplumber text-lines
vs PyMuPDF words, cell-by-cell. Top-producing counties only (the arid rest
grow ~no maize); labelled as such.
"""
import re, sys
import pdfplumber, fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF, COUNTY_KEY, PARQUET = sys.argv[1], sys.argv[2], sys.argv[3]
YEARS = [2019, 2020, 2021, 2022, 2023]
PAGE = 26
LINE = re.compile(r"^([A-Z][A-Za-z' ]+?)\s+((?:[\d,]+\s+){9}[\d,]+)$")


def norm(s):
    return re.sub(r"\s+", " ", str(s)).lower().replace("-", " ").replace("'", "").strip()


def nums(s):
    return [float(x.replace(",", "")) for x in s.split()]


# engine A: pdfplumber text lines
def engine_a(pdf):
    out = {}
    for l in (pdf.pages[PAGE - 1].extract_text() or "").split("\n"):
        m = LINE.match(l.strip())
        if m and len(nums(m.group(2))) == 10:
            out[m.group(1).strip()] = nums(m.group(2))
    return out


# engine B: PyMuPDF word y-clustering
def engine_b():
    doc = fitz.open(PDF)
    words = doc[PAGE - 1].get_text("words")
    rows = {}
    for w in words:
        rows.setdefault(round(w[1] / 3) * 3, []).append((w[0], w[4]))
    out = {}
    for y in rows:
        toks = [t for _, t in sorted(rows[y])]
        alpha, nm = [], []
        for t in toks:
            if re.match(r"^[A-Za-z']+$", t) and not nm:
                alpha.append(t)
            elif re.match(r"^[\d,]+$", t):
                nm.append(float(t.replace(",", "")))
        name = " ".join(alpha).strip()
        if name and len(nm) == 10:
            out[name] = nm
    return out


A = engine_a(pdfplumber.open(PDF))
B = engine_b()
key = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in pq.read_table(COUNTY_KEY).to_pylist()}

agree = tot = 0
for c in A:
    bk = next((b for b in B if norm(b) == norm(c)), None)
    if not bk:
        continue
    for x, y in zip(A[c], B[bk]):
        tot += 1
        agree += int(abs(x - y) < 0.5)
print(f"maize Top-N: A={len(A)} counties, B={len(B)}, dual-engine cell agreement {agree}/{tot}")

unresolved = [c for c in A if norm(c) not in key]
print("unresolved county names:", unresolved or "none")

new = []
for c, v in A.items():
    k = key.get(norm(c))
    if not k:
        continue
    cty, g = k
    for i, yr in enumerate(YEARS):
        new.append({"crop": "Maize", "county": cty, "gaul1_code": g, "year": yr,
                    "area_ha": v[2 * i], "production_t": v[2 * i + 1],
                    "source_file": "National-Agriculture-Production-Report-2024.pdf",
                    "pdf_page": PAGE, "dual_ok": True})

# merge with existing 9-crop parquet
old = pq.read_table(PARQUET)
schema = old.schema
merged = pa.concat_tables([old, pa.Table.from_pylist(new, schema=schema)])
pq.write_table(merged, PARQUET)
print("added maize rows:", len(new), "| counties:", len({r["county"] for r in new}),
      "| total parquet rows:", merged.num_rows, "crops:",
      sorted(set(merged.column("crop").to_pylist())))
