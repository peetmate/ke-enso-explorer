#!/usr/bin/env python3
"""Generic table prober: for (edition, 0-based page, ncells, rotated), report
county count, dual-engine agreement, a sample county row, and the Total row.
Usage: python probe.py <ed> <page> <ncells> <rot0/1> [more triples...]"""
import sys
import fitz, pdfplumber
import pyarrow.parquet as pq
sys.path.insert(0, "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer/_sources")
import napr_extract as NE

BASE = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer"
NE.CANON = {NE.norm(r["county"]): (r["county"], r["gaul1_code"])
            for r in pq.read_table(f"{BASE}/county_key.parquet").to_pylist()}
D = "/Users/pstewarda/Library/CloudStorage/OneDrive-CGIAR/ClimateActionNetZero/1_Projects/D409_Adaptation _Atlas/2_Technical & Data/RCMRD/ENSO explorer/KNBS/Ag Production Reports"
DOC = {"24": [fitz.open(f"{D}/National-Agriculture-Production-Report-2024.pdf"),
              pdfplumber.open(f"{D}/National-Agriculture-Production-Report-2024.pdf")],
       "25": [fitz.open(f"{D}/National-Agriculture-Production-Report-2025.pdf"),
              pdfplumber.open(f"{D}/National-Agriculture-Production-Report-2025.pdf")]}


def probe(ed, page, nc, rot):
    d, l = DOC[ed]
    mu = NE._rows_pymupdf(d, page, rot); pp = NE._rows_pdfplumber(l, page, rot)
    cm = NE._centers(mu, nc); cp = NE._centers(pp, nc)
    a, ta, _ = NE._extract_rows(mu, cm, nc) if cm else ({}, None, [])
    b, _, _ = NE._extract_rows(pp, cp, nc) if cp else ({}, None, [])
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
    smp = next(((k, [round(x, 1) if x is not None else None for x in v]) for k, v in a.items()), None)
    print(f"ed{ed} p{page+1} nc={nc} rot={rot}: cty={len(a)} dual={round(ag/tot,3) if tot else 0} "
          f"total={[round(x,1) if x is not None else None for x in ta] if ta else None}")
    print(f"   sample={smp}")


args = sys.argv[1:]
for i in range(0, len(args), 4):
    probe(args[i], int(args[i+1]), int(args[i+2]), bool(int(args[i+3])))
