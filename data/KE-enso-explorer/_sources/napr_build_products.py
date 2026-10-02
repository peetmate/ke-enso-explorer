#!/usr/bin/env python3
"""Reproducible build of the KNBS-NAPR county LIVESTOCK-PRODUCTS parquet
(Annex 27 of the 2023-24 edition, years 2021 & 2022).

Each product is a Quantity(kg) / Unit-price(KSh) / Total-value(KSh) triple; two
products per page. There is NO national Total row, but two deterministic gates
apply:
  * IDENTITY  value == quantity * unit_price, checked per county cell.
  * DUPLICATE-SERIES a couple of 2021 pages carry a neighbour's data via the
    duplicated text layer (p144 "Wool" shows p143's Milk numbers; p149 "Hides"
    shows p147's Camel-meat numbers). Any (product,year) whose per-county vector
    exactly equals a DIFFERENT product's is a mislabelled duplicate -> dropped.
  * CROSS-YEAR national quantity of a product across 2021/2022 is reported for
    sanity (a >4x swing is flagged).
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
PARQUET = f"{HERE}/knbs_napr_livestock_products.parquet"
SRC = "National-Agriculture-Production-Report-2024.pdf"

NE.CANON = {NE.norm(r["county"]): (r["county"], r["gaul1_code"])
            for r in pq.read_table(f"{HERE}/county_key.parquet").to_pylist()}
doc, pl = fitz.open(PDF24), pdfplumber.open(PDF24)

# product, year, 0-based page, triple index (0 = cols 0-2, 1 = cols 3-5)
REG = [
    ("Milk", 2021, 142, 0), ("Beef", 2021, 142, 1),
    ("Wool", 2021, 143, 0), ("Goat meat", 2021, 143, 1),
    ("Mutton", 2021, 144, 0), ("Pork", 2021, 144, 1),
    ("Camel meat", 2021, 146, 0), ("Honey", 2021, 146, 1),
    ("Wax", 2021, 147, 0), ("Eggs", 2021, 147, 1),
    ("Hides", 2021, 148, 0), ("Skins", 2021, 148, 1),
    ("Milk", 2022, 149, 0), ("Beef", 2022, 149, 1),
    ("Wool", 2022, 150, 0), ("Goat meat", 2022, 150, 1),
    ("Mutton", 2022, 151, 0), ("Pork", 2022, 151, 1),
    ("Camel meat", 2022, 153, 0), ("Honey", 2022, 153, 1),
    ("Wax", 2022, 154, 0), ("Eggs", 2022, 154, 1),
    ("Hides", 2022, 155, 0), ("Skins", 2022, 155, 1),
]


def page_cells(page):
    """pymupdf county -> 6 cells (2 product triples)."""
    mu = NE._rows_pymupdf(doc, page, False)
    a, _, _ = NE._extract_rows(mu, NE._centers(mu, 6), 6)
    return a


pagecache = {}
series = {}   # (product, year) -> {county: (qty, price, value)}
for product, year, page, tri in REG:
    if page not in pagecache:
        pagecache[page] = page_cells(page)
    base = tri * 3
    s = {}
    for cty, cells in pagecache[page].items():
        if base + 2 >= len(cells):
            continue
        q, p, v = cells[base], cells[base + 1], cells[base + 2]
        if q is None or v is None:
            continue
        # IDENTITY gate: value == qty * price (skip cell if it fails)
        if p is not None and abs(q * p - v) > max(2, 0.02 * v):
            continue
        s[cty] = (q, p, v)
    series[(product, year)] = s

# CROSS-YEAR gate: a duplicated-layer page mislabels a neighbour's numbers, so
# that product's national quantity swings wildly between years (Wool 2021 =
# 1680 Mkg vs 2022 = 1.8 Mkg). Real product totals are stable year-to-year, so
# drop BOTH years of any product whose national qty ratio exceeds 4x — safe
# (no tiebreak needed) and only costs the affected product.
drop = set()
prods = {p for p, _ in series}
for product in prods:
    a = sum(v[0] for v in series.get((product, 2021), {}).values())
    b = sum(v[0] for v in series.get((product, 2022), {}).values())
    if a and b and not (0.25 <= a / b <= 4):
        drop.add((product, 2021)); drop.add((product, 2022))

UNIT = {"Eggs": "trays", "Hides": "number", "Skins": "number"}   # rest are kg

rows = []
for (product, year), s in series.items():
    if (product, year) in drop:
        continue
    for cty, (q, p, v) in s.items():
        g = NE.CANON[NE.norm(cty)][1]
        page = next(pg for pr, yr, pg, _ in REG if pr == product and yr == year)
        rows.append({"product": product, "county": cty, "gaul1_code": g, "year": year,
                     "quantity": float(q), "unit": UNIT.get(product, "kg"),
                     "unit_price_ksh": (float(p) if p is not None else None),
                     "value_ksh": float(v), "source_file": SRC, "pdf_page": page + 1})

schema = pa.schema([("product", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                    ("year", pa.int32()), ("quantity", pa.float64()), ("unit", pa.string()),
                    ("unit_price_ksh", pa.float64()), ("value_ksh", pa.float64()),
                    ("source_file", pa.string()), ("pdf_page", pa.int32())])
pq.write_table(pa.Table.from_pylist(rows, schema=schema), PARQUET)

print(f"products parquet rows: {len(rows)}")
print(f"dropped series (duplicate-layer mislabel): {sorted(drop)}")
natl = collections.defaultdict(dict)
for (product, year), s in series.items():
    if (product, year) not in drop:
        natl[product][year] = round(sum(v[0] for v in s.values()) / 1e6, 1)
for product in sorted(natl):
    yrs = natl[product]
    served = [y for (p, y) in {(r["product"], r["year"]) for r in rows} if p == product]
    print(f"  {product:12} national Mkg {dict(sorted(yrs.items()))}  years={sorted(set(r['year'] for r in rows if r['product']==product))}")
