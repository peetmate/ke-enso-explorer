#!/usr/bin/env python3
"""Full audit: every page in both NAPR PDFs with >=4 resolving county rows,
its best orientation, county count, ncells guess, and title. Cross-references
against what is already served (crops/livestock/products parquets) so nothing
county-level is silently un-mined."""
import re, sys, collections
import fitz
import pyarrow.parquet as pq

sys.path.insert(0, "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer/_sources")
import napr_extract as NE

BASE = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer"
NE.CANON = {NE.norm(r["county"]): (r["county"], r["gaul1_code"])
            for r in pq.read_table(f"{BASE}/county_key.parquet").to_pylist()}
D = "/Users/pstewarda/Library/CloudStorage/OneDrive-CGIAR/ClimateActionNetZero/1_Projects/D409_Adaptation _Atlas/2_Technical & Data/RCMRD/ENSO explorer/KNBS/Ag Production Reports"

# pages already served (0-based), by build registries
SERVED_PAGES = {
    "2024": {113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124,  # food annexes
             55, 124, 127,           # cotton, coffee, lint (coffee page 124 dup ok)
             81, 84, 88,             # macadamia(held), groundnut, sunflower
             89,                     # castor(held)
             128, 129, 130, 131, 132, 133, 134, 135, 136,  # livestock pop 15-23
             142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155},  # products 27
    "2025": {185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200,  # food
             126, 127},              # coconut, cashew
}


def scan(pdf, label, ed):
    doc = fitz.open(pdf)
    print(f"\n######### {label} ({doc.page_count} pp) #########")
    for p in range(doc.page_count):
        best = None
        for rot in (True, False):
            rows = NE._rows_pymupdf(doc, p, rot)
            cs, lens = set(), []
            for r in rows:
                nm, nn = NE._name_and_nums(r)
                if NE.resolve(nm) and nn:
                    cs.add(NE.resolve(nm)[0]); lens.append(len(nn))
            n = len(cs)
            nc = collections.Counter(lens).most_common(1)[0][0] if lens else 0
            if best is None or n > best[0]:
                best = (n, rot, nc)
        n, rot, nc = best
        if n >= 4:
            t = re.sub(r"\s+", " ", doc[p].get_text("text"))
            m = re.search(r"(Annex\s*\d+|Table\s*[\d.]+\s*[a-z()]*)\s*[:.]?\s*([^0-9]{0,55})", t)
            title = (m.group(0).strip() if m else t[:55]).strip()
            served = "SERVED " if p in SERVED_PAGES[ed] else "  ???  "
            print(f"  {served} p{p+1:<4} n={n:<3} rot={str(rot):<5} nc={nc:<3} | {title[:60]}")


scan(f"{D}/National-Agriculture-Production-Report-2024.pdf", "NAPR 2024", "2024")
scan(f"{D}/National-Agriculture-Production-Report-2025.pdf", "NAPR 2025", "2025")
