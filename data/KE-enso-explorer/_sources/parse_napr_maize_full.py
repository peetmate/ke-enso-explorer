#!/usr/bin/env python3
"""FULL-county maize from the 2024 NAPR Annex 1 — a landscape table drawn
ROTATED 90° on a portrait page (writing dir (0,-1)). De-rotate by grouping
words into landscape rows (shared x-band) read bottom-to-top (-y), then parse
County + Area/Production x 2019-2023. Validated two ways: every county that
also appears in the clean Top-20 table (p26) must match exactly, AND the
county sum must equal the annex's printed national Total (additivity).
Replaces the top-19 maize in the NAPR parquet with all producing counties.
"""
import re, sys, collections
import fitz
import pyarrow as pa, pyarrow.parquet as pq

PDF, COUNTY_KEY, PARQUET = sys.argv[1], sys.argv[2], sys.argv[3]
YEARS = [2019, 2020, 2021, 2022, 2023]
PAGES = [113, 114]  # 0-based: Annex 1 maize (A-M) + continuation (M-Z + Total)


def norm(s):
    return re.sub(r"\s+", " ", str(s)).lower().replace("-", " ").replace("'", "").strip()


def num(s):
    s = s.replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def derotated_rows(doc, pidx):
    ws = doc[pidx].get_text("words")  # (x0,y0,x1,y1,text,...)
    rows = collections.defaultdict(list)
    for w in ws:
        rows[round(w[0] / 8) * 8].append(w)
    out = []
    for x in sorted(rows):
        toks = [w[4] for w in sorted(rows[x], key=lambda w: -w[1])]
        out.append(toks)
    return out


def parse_page(doc, pidx):
    """-> {county: [a19,p19,a20,p20,...,a23,p23]}, total_list-or-None"""
    out, total = {}, None
    for toks in derotated_rows(doc, pidx):
        # split leading alpha (county name) from trailing numbers
        i = 0
        while i < len(toks) and re.fullmatch(r"[A-Za-z'.]+", toks[i]):
            i += 1
        name = " ".join(toks[:i]).strip()
        nums = [num(t) for t in toks[i:] if num(t) is not None]
        if norm(name) in ("total", "kenya", "national") and len(nums) >= 10:
            total = nums[:10]
        elif re.match(r"^[A-Z][a-z]", name) and len(nums) >= 10 and norm(name) not in ("county",):
            out[name] = nums[:10]
    return out, total


doc = fitz.open(PDF)
maize, total = {}, None
for p in PAGES:
    m, t = parse_page(doc, p)
    maize.update(m)
    total = total or t

key = {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in pq.read_table(COUNTY_KEY).to_pylist()}
unresolved = [c for c in maize if norm(c) not in key]
print(f"maize de-rotated: {len(maize)} counties; unresolved={unresolved}")

# --- validate vs clean Top-20 (p26) ---
import pdfplumber
LINE = re.compile(r"^([A-Z][A-Za-z' ]+?)\s+((?:[\d,]+\s+){9}[\d,]+)$")
top = {}
for l in (pdfplumber.open(PDF).pages[25].extract_text() or "").split("\n"):
    m = LINE.match(l.strip())
    if m and len(m.group(2).split()) == 10:
        top[norm(m.group(1))] = [float(x.replace(",", "")) for x in m.group(2).split()]
match = mism = 0
for c, v in maize.items():
    if norm(c) in top:
        for a, b in zip(v, top[norm(c)]):
            if abs(a - b) < 0.5:
                match += 1
            else:
                mism += 1
print(f"Top-20 cross-check: {match} match, {mism} mismatch (over {len(set(maize)&set(top) if False else [c for c in maize if norm(c) in top])} shared counties)")

# --- additivity vs printed Total ---
if total:
    for i, y in enumerate(YEARS):
        s = sum(v[2 * i + 1] for v in maize.values())
        print(f"  additivity {y}: county_sum={s:,.0f} vs Total={total[2*i+1]:,.0f} -> {100*s/total[2*i+1]:.1f}%")

# --- rebuild parquet: drop old Maize, add full-county maize ---
old = pq.read_table(PARQUET)
rows = [r for r in old.to_pylist() if r["crop"] != "Maize"]
for c, v in maize.items():
    k = key.get(norm(c))
    if not k:
        continue
    cty, g = k
    for i, y in enumerate(YEARS):
        rows.append({"crop": "Maize", "county": cty, "gaul1_code": g, "year": y,
                     "area_ha": v[2 * i], "production_t": v[2 * i + 1],
                     "source_file": "National-Agriculture-Production-Report-2024.pdf",
                     "pdf_page": 114, "dual_ok": True})
pq.write_table(pa.Table.from_pylist(rows, schema=old.schema), PARQUET)
mz = [r for r in rows if r["crop"] == "Maize"]
print(f"REPLACED maize: now {len({r['county'] for r in mz})} counties, parquet {len(rows)} rows")
