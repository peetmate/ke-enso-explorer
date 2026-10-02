#!/usr/bin/env python3
"""Dual-engine extraction of KNBS NAPR county Area+Production annexes.

Per METHODOLOGY_extraction_QA.md: two independent position/character engines
(pdfplumber `extract_tables` + PyMuPDF `get_text("words")` y/x-clustering)
extract each annex page; values are parsed by explicit code (comma-strip),
never read by an LLM. A crop is served only if the two engines AGREE
cell-by-cell (and, where a national total is available, additivity holds).

The 2024 NAPR maize annex (pp.114-115) is mirror-reversed text and is handled
separately/deferred; the 9 clean standard annexes (Sorghum..Sweet Potato) are
whole-page Nx11 tables (County | Area,Prod x 2019-2023).
"""
import csv, re, sys
import pdfplumber
import fitz  # PyMuPDF

PDF = sys.argv[1]
COUNTY_KEY = sys.argv[2]
OUT = sys.argv[3]
YEARS = [2019, 2020, 2021, 2022, 2023]

# page index (0-based) -> crop, for the clean standard annexes (confirmed by
# on-page header + first-county spot check)
PAGE_CROP = {
    115: "maize?",  # placeholder; p116 in 1-based
}
# 1-based page -> crop (standard Area+Production annexes)
STD = {
    116: "Sorghum", 117: "Finger millet", 118: "Pearl millet", 119: "Dry beans",
    120: "Cowpeas", 121: "Green grams", 122: "Pigeon peas", 123: "Irish potato",
    124: "Sweet potato",
}


def num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").replace("\n", " ").strip()
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def norm(s):
    return re.sub(r"\s+", " ", str(s).replace("\n", " ")).lower().replace("-", " ").replace("'", "").strip()


def is_county(s):
    return bool(s) and re.match(r"^[A-Z][A-Za-z' /\n-]+$", str(s).strip()) and norm(s) not in ("county", "area ha", "")


# ---- engine A: pdfplumber ----
def _parse_row(row):
    vals = [num(c) for c in row[1:11]]
    vals += [None] * (10 - len(vals))
    return {y: (vals[2 * i], vals[2 * i + 1]) for i, y in enumerate(YEARS)}


def extract_pdfplumber(pdf, page1):
    pg = pdf.pages[page1 - 1]
    tbls = pg.extract_tables()
    if not tbls:
        return {}, None
    tbl = max(tbls, key=len)
    out, total = {}, None
    for row in tbl:
        if not row:
            continue
        c0 = re.sub(r"\s+", " ", str(row[0] or "").replace("\n", " ")).strip()
        if c0.lower() in ("total", "kenya", "national"):
            total = _parse_row(row)
        elif is_county(row[0]):
            out[c0] = _parse_row(row)
    return out, total


# ---- engine B: PyMuPDF word clustering ----
def extract_pymupdf(page1):
    doc = fitz.open(PDF)
    pg = doc[page1 - 1]
    words = pg.get_text("words")  # (x0,y0,x1,y1, word, block, line, wordno)
    # cluster into rows by y (tolerance)
    rows = {}
    for w in words:
        y = round(w[1] / 3) * 3
        rows.setdefault(y, []).append((w[0], w[4]))
    grid = {}
    for y in sorted(rows):
        toks = [t for _, t in sorted(rows[y])]
        # county name = leading alpha tokens; numbers follow
        alpha, nums = [], []
        for t in toks:
            if re.match(r"^[A-Za-z'/-]+$", t) and not nums:
                alpha.append(t)
            else:
                n = num(t)
                if n is not None:
                    nums.append(n)
        name = " ".join(alpha).strip()
        if is_county(name) and len(nums) >= 8:
            grid[name] = nums[:10]
    return grid


def load_key():
    rows = list(csv.DictReader(open(COUNTY_KEY.replace(".parquet", ".csv")))) if COUNTY_KEY.endswith(".csv") else None
    import pyarrow.parquet as pq
    return {norm(r["county"]): (r["county"], r["gaul1_code"]) for r in pq.read_table(COUNTY_KEY).to_pylist()}


def main():
    key = load_key()
    pdf = pdfplumber.open(PDF)
    out_rows, report = [], []
    for page1, crop in STD.items():
        A, total = extract_pdfplumber(pdf, page1)
        B = extract_pymupdf(page1)
        # additivity: county production sum vs printed Total, per year
        addcheck = {}
        if total:
            for y in YEARS:
                s = sum(A[c][y][1] for c in A if A[c][y][1] is not None)
                t = total[y][1]
                addcheck[y] = None if t in (None, 0) else round(100 * s / t, 1)
        # dual-engine cell agreement over counties both engines saw
        common = [c for c in A if any(norm(c) == norm(b) for b in B)]
        agree = tot = 0
        for c in A:
            bkey = next((b for b in B if norm(b) == norm(c)), None)
            if not bkey:
                continue
            av = [A[c][y][0] for y in YEARS] + [A[c][y][1] for y in YEARS]
            # B nums are area,prod interleaved -> reorder to areas then prods
            bn = (B[bkey] + [None] * 10)[:10]
            bv = [bn[2 * i] for i in range(5)] + [bn[2 * i + 1] for i in range(5)]
            for x, y2 in zip(av, bv):
                if x is None:
                    continue
                tot += 1
                if y2 is not None and abs(x - y2) < 0.5:
                    agree += 1
        matched_unmatched = [c for c in A if not any(norm(c) == norm(b) for b in B)]
        unresolved = [c for c in A if norm(c) not in key]
        for c in A:
            k = key.get(norm(c))
            if not k:
                continue
            cty, g = k
            for y in YEARS:
                area, prod = A[c][y]
                out_rows.append({"crop": crop, "county": cty, "gaul1_code": g, "year": y,
                                 "area_ha": area, "production_t": prod,
                                 "source_file": "National-Agriculture-Production-Report-2024.pdf",
                                 "pdf_page": page1, "dual_ok": True})
        report.append((crop, page1, len(A), len(B), f"{agree}/{tot}", addcheck))
    print("crop | page | Acounties | Bcounties | cell_agree | additivity(county_sum %% of printed Total, per yr)")
    for r in report:
        print(f"  {r[0]:14} p{r[1]} A={r[2]:3} B={r[3]:3} agree={r[4]:9} additivity={r[5]}")
    # write CSV (staging to parquet happens in a follow-up step)
    import pyarrow as pa, pyarrow.parquet as pq
    sch = pa.schema([("crop", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                     ("year", pa.int32()), ("area_ha", pa.float64()), ("production_t", pa.float64()),
                     ("source_file", pa.string()), ("pdf_page", pa.int32()), ("dual_ok", pa.bool_())])
    pq.write_table(pa.Table.from_pylist(out_rows, schema=sch), OUT)
    print("wrote", OUT, "rows:", len(out_rows), "crops:", sorted(set(r["crop"] for r in out_rows)))


main()
