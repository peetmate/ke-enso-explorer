#!/usr/bin/env python3
"""Deterministic extractor for the KNBS County Gender Data Sheets (Oct 2025).

The 47 county sheets are infographic PDFs but every indicator carries a STABLE
CODE (A1, B7, C4, D2, …) that is identical across all counties — so we key on
the code, not the (truncated/typo-prone) label text that fragmented the first
extraction. Each indicator block is followed by value blocks of the form
    "Kenya <County> <kenyaVal> <countyVal>"        (single value), or
    "<Sub> <kenyaVal> <countyVal>" rows under a "Kenya <County>" header (split).

Emits per (county, code[, sub]): canonical label, kenya value, county value.
No number is typed by a model — all parsed from the PDF text. Values are read in
"Kenya then County" column order (matches the printed header on every sheet).

Usage:  <miniforge python> gesi_extract.py <one.pdf>        # inspect one county
        <miniforge python> gesi_extract.py --all <dir>       # all 47 -> parquet
"""
import sys, re, glob, os, collections

import fitz

CODE = re.compile(r"^([A-E]\d{1,2})\s*[:.]\s*(.+)$", re.S)
YEAR = re.compile(r",?\s*(19|20)\d{2}\s*$")
NUM = re.compile(r"-?\d[\d,]*\.?\d*")
# a value line: optional sub-label then >=2 numbers (kenya, county)
COUNTY_FROM_FILE = re.compile(r"^\d+-(.+?)-[Cc]ounty")


def county_of(path):
    base = os.path.basename(path)
    m = COUNTY_FROM_FILE.match(base)
    name = (m.group(1) if m else base).replace("-", " ").strip()
    return name


def clean_label(s):
    s = re.sub(r"\s+", " ", s).strip()
    s = YEAR.sub("", s).strip().rstrip(",")
    return s


def parse_pdf(path):
    doc = fitz.open(path)
    county = county_of(path)
    # gather blocks with column + y, drop page-number blocks
    blocks = []
    for pi in range(doc.page_count):
        for b in doc[pi].get_text("blocks"):
            x0, y0, x1, y1, txt, *_ = b
            t = re.sub(r"[ \t]+", " ", txt).strip()
            if not t or (len(t) <= 3 and t.isdigit()):
                continue
            col = 0 if x0 < 320 else 1
            blocks.append({"pi": pi, "col": col, "x": x0, "y": y0, "t": t})
    # order within a page/column top→bottom
    blocks.sort(key=lambda b: (b["pi"], b["col"], b["y"]))

    # segment into indicator regions: a code block starts a region that runs
    # until the next code block in the same page+column.
    out = []
    i = 0
    n = len(blocks)
    # index code blocks
    idx = [j for j, b in enumerate(blocks) if CODE.match(b["t"].split("\n")[0])]
    for k, j in enumerate(idx):
        b = blocks[j]
        m = CODE.match(b["t"].split("\n")[0])
        code, rawlabel = m.group(1), m.group(2)
        label = clean_label(rawlabel)
        # region = blocks after j, same page+col, until next code block
        region = []
        for jj in range(j + 1, n):
            bb = blocks[jj]
            if bb["pi"] != b["pi"] or bb["col"] != b["col"]:
                break
            if CODE.match(bb["t"].split("\n")[0]):
                break
            region.append(bb)
        rows = parse_region(region, county)
        for sub, kv, cv in rows:
            out.append({"county": county, "code": code, "label": label,
                        "sub": sub, "kenya": kv, "county_value": cv})
    return county, out


def _nums(s):
    return [float(x.replace(",", "")) for x in NUM.findall(s)]


def parse_region(region, county):
    """Return [(sub, kenya, county_value)] for one indicator region.

    Handles the two common layouts:
      inline:   "Kenya <County> k c"               -> (None, k, c)
      split:    header "Kenya <County>" + rows "<Sub> k c"  -> (Sub, k, c)
    Chart-only regions (values with no clean Kenya/County pairing) yield nothing
    and are reported as uncovered.
    """
    YEARTOK = re.compile(r"\b(19|20)\d{2}\b")
    cfirst = county.split()[0].lower()
    def fix_sub(s):
        s = clean_label(s).strip(" :-()")
        low = s.lower()
        if not s or low in ("kenya", county.lower(), cfirst) or s.replace(".", "").isdigit():
            return None
        return s
    rows = []
    for b in region:
        line = re.sub(r"\s+", " ", b["t"]).strip()
        low = line.lower()
        if YEARTOK.search(line):        # caption / label line, not a value row
            continue
        has_kenya = "kenya" in low
        nums = _nums(line)
        # inline: "Kenya <County> k c"
        if has_kenya and cfirst in low and len(nums) >= 2:
            rows.append((None, nums[0], nums[1]))
            continue
        # split sub-row: "<Sub> k c" (exactly 2 trailing numbers, no 'Kenya')
        if not has_kenya and len(nums) == 2:
            m = re.match(r"^(.*?)\s*(-?\d[\d,]*\.?\d*)\s+(-?\d[\d,]*\.?\d*)$", line)
            if m:
                rows.append((fix_sub(m.group(1)), nums[0], nums[1]))
    # dedupe identical
    seen, uniq = set(), []
    for r in rows:
        key = (r[0], r[1], r[2])
        if key not in seen:
            seen.add(key); uniq.append(r)
    return uniq


def main():
    args = sys.argv[1:]
    if args and args[0] == "--all":
        pdfs = sorted(glob.glob(os.path.join(args[1], "*.pdf")))
        allrows = []
        for p in pdfs:
            allrows += parse_pdf(p)[1]
        # canonical label per code = the longest seen (fullest)
        canon = {}
        for r in allrows:
            if len(r["label"]) > len(canon.get(r["code"], "")):
                canon[r["code"]] = r["label"]
        # VALIDATION GATE: the Kenya national value is identical on all 47 sheets
        # for a given (code,sub). Keep only county rows whose Kenya value matches
        # the modal Kenya (misparses drop out); a series is SERVED if >=40/47
        # counties survive. This is the LLM-independent quality proof.
        byks = collections.defaultdict(list)
        for r in allrows:
            byks[(r["code"], r["sub"])].append(r)
        served, dropped = [], []
        for (code, sub), grp in byks.items():
            ks = [round(x["kenya"], 2) for x in grp]
            modal = collections.Counter(ks).most_common(1)[0][0]
            kept = [x for x in grp if round(x["kenya"], 2) == modal]
            if len(kept) >= 40:
                for x in kept:
                    served.append({"county": x["county"], "code": code, "sub": sub,
                                   "label": canon[code], "kenya": modal,
                                   "county_value": x["county_value"]})
            else:
                dropped.append((code, sub, len(kept)))
        nseries = len({(r["code"], r["sub"]) for r in served})
        ncodes = len({r["code"] for r in served})
        print(f"counties={len(pdfs)} served_rows={len(served)} "
              f"served_series={nseries} served_codes={ncodes}")
        print(f"dropped series (chart-style / inconsistent): {len(dropped)} -> "
              f"{sorted(set(c for c, s, n in dropped))}")
        import pyarrow as pa, pyarrow.parquet as pq
        pq.write_table(pa.Table.from_pylist(served), "data/KE-enso-explorer/gesi_v2.parquet")
        print("wrote data/KE-enso-explorer/gesi_v2.parquet (served, gated)")
    else:
        cty, rows = parse_pdf(args[0])
        print(f"county={cty}  indicators={len({r['code'] for r in rows})}  rows={len(rows)}")
        for r in rows:
            print(f"  {r['code']:4} {(r['sub'] or ''):18.18} K={r['kenya']:>8} C={r['county_value']:>8}  {r['label'][:46]}")


if __name__ == "__main__":
    main()
