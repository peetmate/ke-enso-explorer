#!/usr/bin/env python3
"""Robust, deterministic KNBS-NAPR county-table extractor.

One engine for every county table in the National Agriculture Production
Report PDFs. Design goals (from the review that found dropped counties):
  * ORIENTATION-AWARE  - landscape annexes are drawn rotated 90 (writing dir
    (0,-1)); we detect that and read landscape rows (words grouped by x-band,
    read bottom->top). Normal pages read rows by y, left->right.
  * POSITION / DASH TOLERANT - a "-" or blank is null IN PLACE; cells are
    never collapsed, so sparse rows keep column alignment (this is what
    dropped the 7 cotton counties before).
  * DUAL-ENGINE - pdfplumber words vs PyMuPDF words, compared cell-by-cell.
  * ADDITIVITY - county sum vs the printed Total row, per metric-year.
  * NO LLM NUMBERS - every value parsed by code from the PDF bytes.

parse_table(pdf24/25, spec) -> (rows_long, report) where a spec declares the
page(s), rotation, the per-column (metric, year) layout, and expected counts.
"""
import re, collections
import fitz
import pdfplumber

CANON = None  # set by caller: {norm_name: (canonical, gaul1_code)}
UNIT = {"area": "ha", "production": "t", "value": "KSh", "head": "number",
        "number": "number", "greenleaf": "t", "milk": "litres"}


def norm(s):
    return re.sub(r"\s+", " ", str(s)).lower().replace("-", " ").replace("'", "").replace(".", "").strip()


def cell(t):
    """token -> float, or None for dash/blank/sentinel (kept IN PLACE)."""
    if t is None:
        return None
    s = t.replace(",", "").replace("*", "").strip()
    if s in ("", "-", "..", "…", "n/a", "na"):
        return None
    return float(s) if re.fullmatch(r"-?\d+(?:\.\d+)?", s) else "TEXT"  # "TEXT" = non-numeric token


def _rows_pymupdf(doc, pidx, rotated, yrange=None):
    """rows of (pos, text) pairs. pos = within-row reading coordinate, used
    later for column binning (rotated: -y; normal: x). yrange=(lo,hi) spatially
    crops to one table on a page that carries more than one (by vertical y0)."""
    ws = doc[pidx].get_text("words")  # x0,y0,x1,y1,text,...
    if yrange:
        ws = [w for w in ws if yrange[0] <= w[1] <= yrange[1]]
    groups = collections.defaultdict(list)
    if rotated:
        for w in ws:
            groups[round(w[0] / 8) * 8].append(w)          # x-band = landscape row
        pos = lambda w: -w[1]                               # read bottom->top
    else:
        for w in ws:
            groups[round(w[1] / 4) * 4].append(w)           # y-band = row
        pos = lambda w: w[0]                                # read left->right
    return _merge_wrapped([sorted(((pos(w), w[4]) for w in groups[k])) for k in sorted(groups)])


def _rows_pdfplumber(pl, pidx, rotated, yrange=None):
    pg = pl.pages[pidx]
    ws = pg.extract_words()
    if yrange:
        ws = [w for w in ws if yrange[0] <= w["top"] <= yrange[1]]
    groups = collections.defaultdict(list)
    if rotated:
        for w in ws:
            groups[round(w["x0"] / 8) * 8].append(w)
        pos = lambda w: -w["top"]
    else:
        for w in ws:
            groups[round(w["top"] / 4) * 4].append(w)
        pos = lambda w: w["x0"]
    # pdfplumber returns glyphs of rotated (dir (0,-1)) text in reversed
    # character order; reverse each token so it matches PyMuPDF's reading.
    txt = (lambda w: w["text"][::-1]) if rotated else (lambda w: w["text"])
    return _merge_wrapped([sorted(((pos(w), txt(w)) for w in groups[k])) for k in sorted(groups)])


def _merge_wrapped(rows):
    """A county whose name wraps to two lines (Elgeyo/Marakwet, Trans-/Nzoia)
    can leave its NUMBERS on a nameless band BETWEEN the two name fragments
    (finer than the row pitch). Attach each such nameless-numeric row to the
    immediately-preceding name-only row that resolves to a county, so the data
    is not silently lost. The trailing second fragment then resolves to the
    same county with no numbers and is harmlessly dropped downstream."""
    out = []
    for r in rows:
        starts_num = bool(r) and not re.match(r"[A-Za-z]", r[0][1])
        has_num = any(isinstance(cell(t), float) for _, t in r)
        if starts_num and has_num and out:
            prev = out[-1]
            pname = " ".join(t for _, t in prev if re.fullmatch(r"[A-Za-z'./&()-]+", t)).strip()
            prev_has_num = any(isinstance(cell(t), float) for _, t in prev)
            if not prev_has_num and resolve(pname):
                out[-1] = prev + r     # name fragment + its dangling numbers
                continue
        out.append(r)
    return out


def _name_and_nums(row):
    """leading alpha tokens -> county name; numeric tokens -> [(pos, float)].
    Dashes/blanks/trailing text are simply not numeric, so they contribute no
    (pos, float) pair — column binning fills their slot with None."""
    i = 0
    while i < len(row) and re.fullmatch(r"[A-Za-z'./()&-]+", row[i][1]):
        i += 1
    name = " ".join(t for _, t in row[:i]).strip()
    nums = [(p, cell(t)) for p, t in row[i:] if isinstance(cell(t), float)]
    return name, nums


def _centers(rows, ncells):
    """column x/-y centers from the FULL rows (exactly ncells numeric cells)
    that resolve to a county. Some pages carry a duplicated / x-shifted copy of
    the table (a text layer at a different origin, or pdfplumber vs pymupdf
    reading different mediabox origins); the full rows then fall into >1
    cluster by first-column position. Keep the LARGEST cluster and average it,
    so the grid tracks one clean copy regardless of the shifted twin."""
    fulls = []
    for r in rows:
        name, nums = _name_and_nums(r)
        if resolve(name) and len(nums) == ncells:
            fulls.append([p for p, _ in nums])
    if len(fulls) < 3:
        return _centers_gap(rows, ncells)      # sparse table: no/few full rows
    fulls.sort(key=lambda f: f[0])
    groups = [[fulls[0]]]
    for f in fulls[1:]:
        if f[0] - groups[-1][-1][0] > 50:      # jump => a shifted copy
            groups.append([f])
        else:
            groups[-1].append(f)
    big = max(groups, key=len)
    if len(big) >= 3:
        return [sum(c) / len(c) for c in zip(*big)]
    return _centers_gap(rows, ncells)


def _centers_gap(rows, ncells):
    """Fallback grid for SPARSE tables where no county row is full (every row
    has dash cells, e.g. livestock population with breakdown columns). Pool all
    numeric-token positions from resolved county rows and split at the ncells-1
    largest gaps. Works when the leading columns are dense enough to anchor the
    clusters. Used only when the full-row method yields too few complete rows."""
    pos = []
    for r in rows:
        name, nums = _name_and_nums(r)
        if resolve(name):
            pos += [p for p, _ in nums]
    pos.sort()
    if len(pos) < ncells:
        return None
    cuts = sorted(sorted(range(1, len(pos)), key=lambda i: pos[i] - pos[i - 1],
                         reverse=True)[:ncells - 1])
    centers, start = [], 0
    for c in cuts + [len(pos)]:
        centers.append(sum(pos[start:c]) / (c - start))
        start = c
    return centers


def _cells_by_col(nums, centers):
    """place each numeric token in its nearest column (within half the min
    inter-column gap); unfilled columns stay None. This detects genuinely
    BLANK cells (no glyph) that positional splitting cannot."""
    gap = min((centers[i + 1] - centers[i] for i in range(len(centers) - 1)), default=1e9)
    tol = gap * 0.6
    cells = [None] * len(centers)
    dist = [None] * len(centers)
    for pos, val in nums:
        j = min(range(len(centers)), key=lambda k: abs(centers[k] - pos))
        d = abs(centers[j] - pos)
        if d <= tol and (cells[j] is None or d < dist[j]):
            cells[j], dist[j] = val, d
    return cells


def _extract_rows(rows, centers, ncells):
    """Column-bin each row onto the shared `centers` grid, keyed by county.
    Only rows whose leading name resolves to a canonical county (or the printed
    Total) are kept — excludes narrative prose around in-body tables. If a
    county appears more than once (some 2024 pages carry a duplicated text
    layer shifted in x — its tokens fall outside every column and bin to all
    None), the row with MORE filled cells wins.

    Also returns `missed`: capitalised alpha-led rows carrying >=ncells/2
    numbers that DON'T resolve to a county — a completeness tripwire (a real
    county row the parser failed to attribute). Empty `missed` => every data
    row on the page was captured, so an additivity < 100% is a source property
    (KNBS national Total exceeding the itemised county sum), not a drop."""
    out, total, missed = {}, None, []
    for r in rows:
        name, nums = _name_and_nums(r)
        if not name or not nums:
            continue
        nm = norm(name)
        cells = _cells_by_col(nums, centers)
        if nm in ("total", "kenya", "national", "grand total"):
            if total is None or _filled(cells) > _filled(total):
                total = cells
        elif nm in ("others", "other", "other counties", "rest", "others counties",
                    "all companies", "all", "subtotal", "sub total", "average") \
                or nm.startswith("average yield") or nm.startswith("all companies"):
            continue    # non-county aggregate / footer; explains county-sum < Total
        elif resolve(name) and _filled(cells) > 0:
            # skip all-None rows: a shifted duplicate-layer copy bins to nothing
            # and would otherwise inflate the county count with empty phantoms.
            if name not in out or _filled(cells) > _filled(out[name]):
                out[name] = cells
        elif re.match(r"[A-Z]", name) and len(nums) >= ncells / 2 and not _is_header(name) \
                and not any(resolve(w) for w in name.split()):
            missed.append(name)   # capitalised, numeric, but no word resolves -> real miss
    return out, total, missed


_HDR = re.compile(r"county|area|produc|tonnes|\(ha\)|national|annex|report|value|price|total|"
                  r"year|top|ranking|figure|table|quantity|head|number|\(kg\)|trays|"
                  r"unit|ksh|kshs|tons|kgs?|litres|hives|/|parameter|export|month|"
                  r"january|february|march|april|may|june|july|august|september|october|november|december", re.I)


def _is_header(name):
    return bool(_HDR.search(name))


def _filled(cells):
    return sum(x is not None for x in cells)


def parse_table(doc, pl, spec):
    """spec: {pages:[0based], rotated:bool, ncells:int, layout:[(metric,year),...],
             unit:str, crop:str, category:str}. layout length == ncells."""
    ncells = spec["ncells"]
    A, totalA, missed = {}, None, []
    B = {}
    yr = spec.get("yrange")
    for p in spec["pages"]:
        mu = _rows_pymupdf(doc, p, spec["rotated"], yr)
        pp = _rows_pdfplumber(pl, p, spec["rotated"], yr)
        # each engine on its OWN grid (they can read different mediabox origins
        # -> different x). pymupdf is authoritative for serving; pdfplumber is
        # the independent cross-check. Comparing by county VALUE (below) is
        # origin-independent, so an x-offset between engines doesn't matter.
        cmu, cpp = _centers(mu, ncells), _centers(pp, ncells)
        if not (cmu or cpp):
            continue
        a, ta, ma = _extract_rows(mu, cmu or cpp, ncells)   # SERVE (pymupdf)
        b, _, _ = _extract_rows(pp, cpp or cmu, ncells)     # CHECK (pdfplumber)
        A.update(a); B.update(b)
        missed += ma
        totalA = totalA or ta
    # dual-engine agreement over shared counties/cells. dual_shared = how many
    # counties both engines read: near-0 means pdfplumber failed on this page
    # (duplicate/shifted/garbled layer), so dual can't corroborate and the gate
    # falls back to additivity + completeness (both pymupdf-authoritative).
    agree = tot = shared = 0
    for c in A:
        bk = next((k for k in B if norm(k) == norm(c)), None)
        if not bk:
            continue
        shared += 1
        for x, y in zip(A[c], B[bk]):
            if x is None:
                continue
            tot += 1
            agree += int(y is not None and abs(x - y) < max(0.5, 0.001 * abs(x)))
    dual = agree / tot if tot else 0.0
    # additivity per (metric,year) column vs printed Total
    add = {}
    if totalA:
        for j, (metric, year) in enumerate(spec["layout"]):
            s = sum(v[j] for v in A.values() if v[j] is not None)
            t = totalA[j]
            add[(metric, year)] = None if not t else round(100 * s / t, 1)
    # emit long rows
    rows = []
    for c, v in A.items():
        cty, g = resolve(c)
        for j, (metric, year) in enumerate(spec["layout"]):
            if v[j] is None:
                continue
            rows.append({"edition": spec["edition"], "crop": spec["crop"], "category": spec["category"],
                         "county": cty, "gaul1_code": g, "year": year, "metric": metric,
                         "value": v[j], "unit": UNIT.get(metric, ""), "source_file": spec["src"],
                         "pdf_page": spec["pages"][0] + 1})
    report = {"crop": spec["crop"], "edition": spec["edition"], "pages": [p + 1 for p in spec["pages"]],
              "counties": len(A), "dual_engine": round(dual, 3), "dual_shared": shared,
              "additivity": add, "missed": sorted(set(missed))}
    return rows, report


# explicit PDF-typo aliases (deterministic, audited — NOT blind fuzzy, which
# can mis-map one county onto another and silently corrupt the data).
ALIAS = {"kiliif": "kilifi", "muranga": "murang'a", "tharaka": "tharaka nithi",
         "elgeyo": "elgeyo marakwet", "taita": "taita taveta", "uasin": "uasin gishu",
         "trans": "trans nzoia", "homa": "homa bay", "west": "west pokot",
         # bare 2nd words of wrapped two-word names (orphaned onto their own row
         # when the name wraps). Safe: on a duplicate, the fuller row wins.
         "nithi": "tharaka nithi", "marakwet": "elgeyo marakwet",
         "taveta": "taita taveta", "nzoia": "trans nzoia", "gishu": "uasin gishu",
         # slash-abbreviated names seen in the cash-crop tables
         "e/marakwet": "elgeyo marakwet", "t/nithi": "tharaka nithi",
         "t/nzoia": "trans nzoia", "u/gishu": "uasin gishu", "taita/taveta": "taita taveta",
         # two-word names printed with no space
         "homabay": "homa bay", "tanariver": "tana river", "transnzoia": "trans nzoia",
         "westpokot": "west pokot", "uasingishu": "uasin gishu", "elgeyomarakwet": "elgeyo marakwet",
         "tharakanithi": "tharaka nithi", "taitataveta": "taita taveta", "nairobicity": "nairobi city"}


def resolve(name):
    """canonical county: exact -> explicit typo alias -> unique 2-word prefix.
    No fuzzy matching (would risk mapping one county onto a different one)."""
    n = norm(name)
    if not n or len(n) < 3:
        return None
    if n in CANON:
        return CANON[n]
    if n in ALIAS and ALIAS[n] in CANON:
        return CANON[ALIAS[n]]
    pre = [v for k, v in CANON.items() if k.startswith(n + " ")]
    return pre[0] if len(pre) == 1 else None
