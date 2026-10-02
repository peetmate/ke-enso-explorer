#!/usr/bin/env python3
"""Reproducible build of the KNBS-NAPR county LIVESTOCK parquet (2023-24 edition).

Population annexes 15-26 give animal counts for 2021/2022/2023 (one annex per
year per animal family). Unlike the crop annexes they have NO printed Total row
and NO headline-in-data column (Cattle = Dairy_Cattle + Beef_Cattle etc. are
spanning labels over sub-columns), so additivity can't validate them. Two
deterministic checks are used instead:

  * DUAL-ENGINE where pdfplumber can read the page. pdfplumber garbles a
    duplicated/shifted text layer on ~half the pages (page-specific); pymupdf
    reads every page cleanly, so it is authoritative.
  * CROSS-YEAR plausibility for the pdfplumber-garbled years: a county's count
    must sit within +/-50% of the median of its dual-CONFIRMED years for that
    species (livestock populations don't swing that hard year to year). A column
    mis-read would land wildly off and be dropped.

Species that are dense standalone / clean sub-column sums are served; the sparse
beehive-type and exotic-poultry sub-columns (Annex 24-26) are not extracted.
NO number is read or typed by a model.
"""
import sys, collections
import fitz, pdfplumber
import pyarrow as pa, pyarrow.parquet as pq

HERE = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer"
sys.path.insert(0, HERE + "/_sources")
import napr_extract as NE

D = "/Users/pstewarda/Library/CloudStorage/OneDrive-CGIAR/ClimateActionNetZero/1_Projects/D409_Adaptation _Atlas/2_Technical & Data/RCMRD/ENSO explorer/KNBS/Ag Production Reports"
PDF24 = sys.argv[1] if len(sys.argv) > 1 else f"{D}/National-Agriculture-Production-Report-2024.pdf"
PARQUET = f"{HERE}/knbs_napr_livestock.parquet"
SRC = "National-Agriculture-Production-Report-2024.pdf"

NE.CANON = {NE.norm(r["county"]): (r["county"], r["gaul1_code"])
            for r in pq.read_table(f"{HERE}/county_key.parquet").to_pylist()}
doc, pl = fitz.open(PDF24), pdfplumber.open(PDF24)

# family: ncells, {year: 0-based page}, {species: [col indices to sum]}
FAMILIES = [
    dict(ncells=6, pages={2021: 128, 2022: 129, 2023: 130},
         species={"Cattle": [0, 1], "Sheep": [2, 3], "Goats": [4, 5]}),
    dict(ncells=6, pages={2021: 131, 2022: 132, 2023: 133},
         species={"Donkeys": [0], "Camels": [1]}),   # beehive sub-cols too sparse to trust
    dict(ncells=5, pages={2021: 134, 2022: 135, 2023: 136},
         species={"Pigs": [0], "Rabbits": [1], "Broiler chicken": [2],
                  "Layer chicken": [3], "Indigenous chicken": [4]}),
    # other poultry (Annex 24-26); only the dense leading columns are served
    # (guinea fowl / pigeons / doves / quails / ostrich are too sparse to trust)
    dict(ncells=8, pages={2021: 137, 2022: 138, 2023: 139},
         species={"Turkeys": [0], "Ducks": [1], "Geese": [2]}),
]


def extract(page, ncells):
    """pymupdf county -> cells (authoritative), plus dual-engine agreement."""
    mu = NE._rows_pymupdf(doc, page, False)
    pp = NE._rows_pdfplumber(pl, page, False)
    a, _, _ = NE._extract_rows(mu, NE._centers(mu, ncells), ncells)
    b, _, _ = NE._extract_rows(pp, NE._centers(pp, ncells), ncells)
    ag = tot = 0
    for c in a:
        bk = next((k for k in b if NE.norm(k) == NE.norm(c)), None)
        if not bk:
            continue
        for x, y in zip(a[c], b[bk]):
            if x is None:
                continue
            tot += 1
            ag += y is not None and abs(x - y) < max(1, 0.001 * abs(x))
    return a, (ag / tot if tot else 0.0)


def headline(cells, idxs):
    """sum of sub-columns; a dash sub-column counts as 0, but at least one must
    be present (else the animal is genuinely unreported -> None)."""
    vals = [cells[i] for i in idxs if i < len(cells) and cells[i] is not None]
    return sum(vals) if vals else None


rows, report = [], []
for fam in FAMILIES:
    nc = fam["ncells"]
    # per year: {county: cells}, dual
    peryear, dual = {}, {}
    for yr, pg in fam["pages"].items():
        peryear[yr], dual[yr] = extract(pg, nc)
    confirmed = {yr for yr in peryear if dual[yr] >= 0.98}
    for sp, idxs in fam["species"].items():
        # confirmed-year values per county for the cross-year baseline
        base = collections.defaultdict(list)
        for yr in confirmed:
            for cty, cells in peryear[yr].items():
                h = headline(cells, idxs)
                if h is not None:
                    base[cty].append(h)
        served = dropped = 0
        for yr in fam["pages"]:
            pg = fam["pages"][yr]
            for cty, cells in peryear[yr].items():
                h = headline(cells, idxs)
                if h is None:
                    continue
                if yr in confirmed:
                    ok = True
                else:  # garbled page: cross-year plausibility vs confirmed years
                    med = sorted(base.get(cty, []))
                    m = med[len(med) // 2] if med else None
                    ok = m is not None and abs(h - m) <= 0.5 * max(m, 1)
                if not ok:
                    dropped += 1
                    continue
                served += 1
                g = NE.CANON[NE.norm(cty)][1]
                rows.append({"species": sp, "county": cty, "gaul1_code": g, "year": yr,
                             "head": float(h), "source_file": SRC, "pdf_page": pg + 1})
        method = {yr: ("dual" if yr in confirmed else "pymupdf+cross-year") for yr in fam["pages"]}
        report.append((sp, served, dropped, dual, method))

schema = pa.schema([("species", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                    ("year", pa.int32()), ("head", pa.float64()),
                    ("source_file", pa.string()), ("pdf_page", pa.int32())])
pq.write_table(pa.Table.from_pylist(rows, schema=schema), PARQUET)

print(f"livestock parquet rows: {len(rows)}")
for sp, served, dropped, dual, method in report:
    du = {y: round(v, 2) for y, v in dual.items()}
    print(f"  {sp:20} served={served:3} dropped={dropped:2}  dual={du}")
print("species:", sorted(set(r["species"] for r in rows)))
print("years:", sorted(set(r["year"] for r in rows)))
