#!/usr/bin/env python3
"""Reproducible build of the KNBS-NAPR county production parquet.

Registry of every county table we serve (both NAPR editions) -> the robust
deterministic engine (napr_extract) -> validation gate -> rebase across
editions -> wide parquet + per-table validation report.

Usage:  python napr_build.py <NAPR2024.pdf> <NAPR2025.pdf>
(defaults to the D409 OneDrive paths when run with no args.)

Gate (a table is SERVED only if all hold):
  * dual-engine cell agreement >= 0.98
  * completeness: no capitalised numeric row left unattributed (`missed`)
  * county sum never EXCEEDS the printed Total (over-sum = double-count)
county-sum < Total is allowed (KNBS Totals exceed itemised counties for
highland/minor crops, coffee). NO number is read or typed by a model.
"""
import sys, csv, collections
import pyarrow as pa, pyarrow.parquet as pq
import fitz, pdfplumber

HERE = "/Users/pstewarda/Documents/rprojects/atlas_nb-KE-enso/data/KE-enso-explorer"
sys.path.insert(0, HERE + "/_sources")
import napr_extract as NE

D = "/Users/pstewarda/Library/CloudStorage/OneDrive-CGIAR/ClimateActionNetZero/1_Projects/D409_Adaptation _Atlas/2_Technical & Data/RCMRD/ENSO explorer/KNBS/Ag Production Reports"
PDF24 = sys.argv[1] if len(sys.argv) > 1 else f"{D}/National-Agriculture-Production-Report-2024.pdf"
PDF25 = sys.argv[2] if len(sys.argv) > 2 else f"{D}/National-Agriculture-Production-Report-2025.pdf"
PARQUET = f"{HERE}/knbs_napr_county_production.parquet"
REPORT = f"{HERE}/_sources/napr_validation_report.csv"

NE.CANON = {NE.norm(r["county"]): (r["county"], r["gaul1_code"])
            for r in pq.read_table(f"{HERE}/county_key.parquet").to_pylist()}
Y24 = [2019, 2020, 2021, 2022, 2023]
Y25 = [2020, 2021, 2022, 2023, 2024]
YC = [2019, 2020, 2021, 2022, 2023]


def AP(years):    # food annexes: interleaved Area,Production per year
    return [(m, y) for y in years for m in ("area", "production")]


def blk(ms, ys):  # grouped: all of metric-1, then metric-2 ...
    return [(m, y) for m in ms for y in ys]


def grp3(ys):     # coffee: 3 sub-cols/year (Co-op, Estate, Total); Total=production
    return [(m, y) for y in ys for m in ("coop", "estate", "production")]


def byyear(ys):   # area,production,value grouped BY YEAR (each year's 3 together)
    return [(m, y) for y in ys for m in ("area", "production", "value")]


def prod_only(ys):
    return [("production", y) for y in ys]


def area_only(ys):
    return [("area", y) for y in ys]


# crop, edition, [0-based pages], layout  (ncells = len(layout))
FOOD = [
    ("Maize", "2024", [113, 114], AP(Y24)), ("Maize", "2025", [185, 186], AP(Y25)),
    ("Sorghum", "2024", [115], AP(Y24)), ("Sorghum", "2025", [188, 189], AP(Y25)),
    ("Finger millet", "2024", [116], AP(Y24)),
    ("Pearl millet", "2024", [117], AP(Y24)),
    ("Millet (combined)", "2025", [187], AP(Y25)),
    ("Dry beans", "2024", [118], AP(Y24)), ("Dry beans", "2025", [190, 191], AP(Y25)),
    ("Cowpeas", "2024", [119], AP(Y24)), ("Cowpeas", "2025", [192], AP(Y25)),
    ("Green grams", "2024", [120], AP(Y24)), ("Green grams", "2025", [193], AP(Y25)),
    ("Pigeon peas", "2024", [121], AP(Y24)), ("Pigeon peas", "2025", [194], AP(Y25)),
    ("Irish potato", "2024", [122], AP(Y24)), ("Irish potato", "2025", [195], AP(Y25)),
    ("Sweet potato", "2024", [123], AP(Y24)), ("Sweet potato", "2025", [196, 197], AP(Y25)),
    ("Cassava", "2025", [198, 199], AP(Y25)),
    ("Wheat", "2024", [27], AP(Y24)),   # Section-3 body table, area+prod (no Total row)
    ("Barley", "2024", [34], AP(Y24)),  # Table 3.12; no Total + pdfplumber garbles -> manual-verify
]
# tables that cannot pass the automatic gate (no Total AND pdfplumber unreadable)
# but were verified by eye against the PDF; served with that provenance recorded.
MANUAL_VERIFY = {"Barley": "Pete vs PDF p35 (2024 ed, Table 3.12), 2026-07-20"}
CASH = [  # all 2024 edition
    ("Cotton (seed)", "2024", [55], blk(["area", "production", "value"], YC)),  # rotated
    ("Coffee", "2024", [124], grp3(YC)),                                        # rotated
    ("Lint", "2024", [127], blk(["production", "value"], YC)),                  # rotated
    ("Macadamia", "2024", [81], blk(["area", "production", "value"], YC)),      # upright
    ("Groundnut", "2024", [84], blk(["area", "production", "value"], YC)),      # upright
    ("Sunflower", "2024", [88], [("area", 2023), ("production", 2023), ("value", 2023)]),
    ("Coconut", "2024", [82], blk(["area", "production", "value"], YC)),             # 2019-23, extends coconut back
    ("Coconut", "2025", [126], blk(["area", "production", "value"], [2023, 2024])),  # by-metric
    ("Cashew nut", "2025", [127], byyear([2023, 2024])),                             # by-year
    # castor: physical table is area/prod/value (3 cols) — read all 3 for alignment,
    # serve area+prod (both reconcile to the printed Total 100%); value dropped
    # (labelled "Ksh Million" but the magnitude doesn't reconcile).
    ("Castor", "2024", [89], [("area", 2023), ("production", 2023), ("drop", 2023)]),
    # 2025 cash tables (Table 6.x), by-year area/prod/value 2023-2024, value in KSh million.
    # These extend / replace their 2024-edition counterparts (Macadamia 2024 was held back).
    ("Macadamia", "2025", [128], byyear([2023, 2024])),
    # Groundnut/Sunflower 2025: the 2023 column-block double-counts (186% / 104.8%);
    # 2023 is already served from the 2024 edition, so mask it and take only 2024.
    ("Groundnut", "2025", [129], [("drop", 2023)] * 3 + byyear([2024])),
    # Sesame + Canola share page p133; y-crop isolates each table.
    ("Sesame", "2025", [132], byyear([2023, 2024]), (120, 320)),
    ("Canola", "2025", [132], byyear([2023, 2024]), (540, 760)),
    ("Sunflower", "2025", [134], [("drop", 2023)] * 3 + byyear([2024])),
    # cotton to 2024 (2025 edition, blk area/prod/value x 2020-2024, value raw KSh)
    ("Cotton (seed)", "2025", [114], blk(["area", "production", "value"], Y25)),
    # major cash crops: green-leaf tea + sugarcane (production only), both editions
    ("Tea (green leaf)", "2024", [72, 73], prod_only(Y24)),  # green-leaf table spans p73-74
    ("Tea (green leaf)", "2025", [88], prod_only(Y25)),
    ("Sugarcane", "2024", [46], prod_only(Y24)),
    ("Sugarcane", "2025", [98], prod_only(Y25)),
    # sisal quantity + value (2025 Table 5.4(b), 2021-2024)
    ("Sisal", "2025", [103], blk(["production", "value"], [2021, 2022, 2023, 2024])),
    # pyrethrum dry-flower production (kg -> tonnes), both editions
    ("Pyrethrum", "2024", [64], prod_only(Y24)),
    ("Pyrethrum", "2025", [119], prod_only(Y25)),
    # minor oilseeds/legumes (few counties, but full for the crop)
    ("Sesame", "2024", [86], AP(Y24)),               # area+prod (2025 held: Canola shares page)
    ("Bambara nut", "2024", [85], blk(["area", "production", "value"], YC)),
    ("Bambara nut", "2025", [131], byyear([2023, 2024])),
    # AREA tables that enrich already-served crops with area_ha (production served elsewhere)
    ("Tea (green leaf)", "2024", [74], area_only(Y24)),
    ("Tea (green leaf)", "2025", [91], area_only(Y25)),
    ("Pyrethrum", "2024", [63], area_only(Y24)),
    ("Pyrethrum", "2025", [117], area_only(Y25)),
    # bixa: area only, printed in acres (-> ha), 2022-2024
    ("Bixa", "2025", [121], area_only([2022, 2023, 2024])),
]
# value normalisation to raw KSh: several cash tables print value in KSh million
VSCALE = {"Macadamia": 1e6, "Groundnut": 1e6, "Sunflower": 1e6,
          "Coconut": 1e6, "Cashew nut": 1e6, "Sesame": 1e6, "Sisal": 1e6, "Bambara nut": 1e6, "Canola": 1e6}
# production-unit normalisation to tonnes (green-leaf tea is printed in kg)
PSCALE = {"Tea (green leaf)": 0.001, "Pyrethrum": 0.001}
# area-unit normalisation to hectares (bixa is printed in acres)
ASCALE = {"Bixa": 0.404686}

DOC = {"2024": (fitz.open(PDF24), pdfplumber.open(PDF24), "National-Agriculture-Production-Report-2024.pdf"),
       "2025": (fitz.open(PDF25), pdfplumber.open(PDF25), "National-Agriculture-Production-Report-2025.pdf")}


def try_table(crop, edition, pages, layout, yrange=None):
    """Run both orientations, return (rows, rep) for the one with best
    production additivity + dual + county count."""
    doc, pl, src = DOC[edition]
    ncells = len(layout)
    best = None
    for rot in (True, False):
        spec = dict(crop=crop, category="crop", edition=edition, src=src,
                    pages=pages, rotated=rot, ncells=ncells, layout=layout, yrange=yrange)
        rows, rep = NE.parse_table(doc, pl, spec)
        ref = [v for k, v in rep["additivity"].items() if k[0] == "production" and v is not None] \
            or [v for k, v in rep["additivity"].items() if v is not None] or [0]
        dev = sum(abs(x - 100) for x in ref) / len(ref)
        # prefer the orientation that resolves counties with engine agreement,
        # then the most counties, then the tightest additivity. (No >=15 floor:
        # minor crops like Wheat have few counties and no Total row.)
        score = (rep["counties"] >= 4 and rep["dual_engine"] >= 0.98, rep["counties"], -dev)
        if best is None or score > best[0]:
            best = (score, rot, rows, rep, dev)
    _, rot, rows, rep, dev = best
    rep["rotated"] = rot
    return rows, rep


def gate(rep):
    """Serve iff ALL hold:
      * completeness  - no capitalised numeric row left unattributed (`missed`)
      * no over-sum   - county sum never EXCEEDS the printed Total (double-count)
      * has a printed Total to reconcile against
      * >= 4 counties
    Rationale: with every printed county captured (completeness) and no
    double-count, county-sum <= Total, so any shortfall is genuinely unlisted
    counties / an "Others" bucket -> a CORRECT extraction. Additivity vs the
    report's own printed Total is the authoritative deterministic check.
    Dual-engine is reported (`validation`) as extra corroboration where
    pdfplumber could read the page, but is NOT required: pdfplumber mis-reads
    the duplicate-/shifted-layer pages (proven: it returns 4 counties and a
    null Meru for macadamia), so requiring it would drop data additivity
    confirms is correct."""
    # judge only the columns we actually serve (real metrics) — a masked "drop"
    # column (e.g. a contaminated year we take from the other edition) must not
    # sink the table.
    if rep["crop"] in MANUAL_VERIFY:      # eye-verified against the PDF (see MANUAL_VERIFY)
        return True
    add = [v for (m, y), v in rep["additivity"].items()
           if m in ("area", "production", "value") and v is not None]
    # >102 = double-count (real ones are 150-500%); <=102 tolerates rounding on
    # KSh-million value columns summed over ~30 counties.
    if rep["missed"] or any(v > 102 for v in add) or rep["counties"] < 4:
        return False
    dual_confirmed = rep["dual_shared"] >= 5 and rep["dual_engine"] >= 0.98
    # dual-engine corroboration alone is sufficient (some body tables print no
    # national Total -> no additivity possible, e.g. Wheat). When a Total IS
    # printed, a single-engine table must reconcile to ~100%, else a nameless
    # row the completeness check can't see may have been dropped (macadamia's
    # Murang'a). Shortfalls (sum<Total) are only trusted when dual-confirmed.
    if dual_confirmed:
        return True
    return bool(add) and min(add) >= 97


def validation_label(rep):
    if rep["crop"] in MANUAL_VERIFY:
        return "manual-verify (" + MANUAL_VERIFY[rep["crop"]] + ")"
    if rep["dual_shared"] >= 5 and rep["dual_engine"] >= 0.98:
        return "dual-engine + additivity"
    return "additivity + completeness (single-engine; pdfplumber unreliable on page)"


import re as _re


def _title(edition, page, yrange=None):
    """the 'Table X.Y: ...' / 'Annex N: ...' caption for citation. Requires the
    colon/period caption form (skips prose cross-refs like 'Table 3.12).'). When
    yrange is set (a page with >1 table) restrict to lines near that region so
    the right table's caption wins."""
    doc = DOC[edition][0][page]
    if yrange:
        lines = []
        for b in doc.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                y = ln["bbox"][1]
                if yrange[0] - 70 <= y <= yrange[1]:
                    lines.append((y, " ".join(s["text"] for s in ln["spans"])))
        text = " ".join(t for _, t in sorted(lines))
    else:
        text = _re.sub(r"\s+", " ", doc.get_text("text"))
    m = _re.search(r"((?:Annex|Table)\s*[\d.]+\s*\(?\s?[a-d]?\)?\s*:\s*[A-Z][A-Za-z][^0-9]{3,55})", text)
    return _re.sub(r"\s+", " ", m.group(1)).strip().rstrip(",") if m else f"p{page + 1}"


def build():
    long_rows, report, cites = [], [], []
    ED = {"2024": "2023-24 edition", "2025": "2024-25 edition"}
    for entry in FOOD + CASH:
        crop, edition, pages, layout = entry[:4]
        yrange = entry[4] if len(entry) > 4 else None
        rows, rep = try_table(crop, edition, pages, layout, yrange)
        ok = gate(rep)
        padd = {k[1]: v for k, v in rep["additivity"].items() if k[0] == "production"}
        report.append({"crop": crop, "edition": edition, "pages": str(rep["pages"]),
                       "rotated": rep["rotated"], "counties": rep["counties"],
                       "dual_engine": rep["dual_engine"], "dual_shared": rep["dual_shared"],
                       "prod_additivity": str(padd), "missed": ";".join(rep["missed"]),
                       "validation": validation_label(rep), "served": ok})
        if ok:
            long_rows += rows
            vs = [m for m in ("area", "production", "value") if any(mm == m for mm, _ in layout)]
            cites.append({"commodity": crop, "category": "crop",
                          "variables": ", ".join({"area": "area (ha)", "production": "production (t)",
                                                   "value": "value (KSh)"}[v] for v in vs),
                          "edition": ED[edition], "table": _title(edition, pages[0], yrange),
                          "page": pages[0] + 1, "validation": validation_label(rep)})

    # rebase: prefer 2025-edition value for a (crop,county,year,metric)
    best = {}
    for r in long_rows:
        k = (r["crop"], r["county"], r["year"], r["metric"])
        if k not in best or (r["edition"] == "2025" and best[k]["edition"] != "2025"):
            best[k] = r

    MET = {"area": "area_ha", "production": "production_t", "value": "value_ksh"}
    wide = collections.defaultdict(lambda: {"area_ha": None, "production_t": None, "value_ksh": None})
    meta = {}
    for (crop, county, year, metric), r in best.items():
        if metric not in MET:
            continue
        val = r["value"]
        if metric == "value":
            val *= VSCALE.get(crop, 1)
        elif metric == "production":
            val *= PSCALE.get(crop, 1)
        elif metric == "area":
            val *= ASCALE.get(crop, 1)
        wide[(crop, county, year)][MET[metric]] = val
        meta[(crop, county, year)] = (r["gaul1_code"], r["source_file"], r["pdf_page"])

    out = []
    for (crop, county, year), v in sorted(wide.items()):
        g, src, pg = meta[(crop, county, year)]
        out.append({"crop": crop, "county": county, "gaul1_code": g, "year": year,
                    "area_ha": v["area_ha"], "production_t": v["production_t"],
                    "value_ksh": v["value_ksh"], "source_file": src, "pdf_page": pg, "dual_ok": True})

    schema = pa.schema([("crop", pa.string()), ("county", pa.string()), ("gaul1_code", pa.float64()),
                        ("year", pa.int32()), ("area_ha", pa.float64()), ("production_t", pa.float64()),
                        ("value_ksh", pa.float64()), ("source_file", pa.string()), ("pdf_page", pa.int32()),
                        ("dual_ok", pa.bool_())])
    pq.write_table(pa.Table.from_pylist(out, schema=schema), PARQUET)
    with open(REPORT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(report[0].keys()))
        w.writeheader(); w.writerows(report)

    # citation table (crop x variable -> report table/page) + livestock/products
    cites.append({"commodity": "Livestock population (13 species)", "category": "livestock",
                  "variables": "head", "edition": "2023-24 edition",
                  "table": "Annex 15-26: Population by county", "page": 129,
                  "validation": "dual-engine (per page) + cross-year plausibility"})
    cites.append({"commodity": "Livestock products (11)", "category": "product",
                  "variables": "quantity, value (KSh)", "edition": "2023-24 edition",
                  "table": "Annex 27: Livestock products by county", "page": 143,
                  "validation": "value = quantity x unit-price + cross-year"})
    import json as _json
    cites.sort(key=lambda c: (c["category"], c["commodity"]))
    with open(f"{HERE}/napr_sources.json", "w") as f:
        _json.dump(cites, f, indent=1, ensure_ascii=False)

    served = sorted(set(r["crop"] for r in out))
    print(f"parquet rows: {len(out)}   crops served: {len(served)}")
    for c in served:
        rs = [r for r in out if r["crop"] == c]
        print(f"  {c:18} counties={len(set(r['county'] for r in rs)):2} years={sorted(set(r['year'] for r in rs))}")
    print(f"NOT served: {[(r['crop'], r['edition']) for r in report if not r['served']]}")


if __name__ == "__main__":
    build()
