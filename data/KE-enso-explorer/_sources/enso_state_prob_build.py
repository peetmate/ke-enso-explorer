#!/usr/bin/env python3
"""Official CPC ENSO-state probability forecast for the KE-ENSO Block-5 outlook (KE-09 layer 3).

Parses the NOAA CPC RONI-based probabilistic ENSO forecast (El Nino / ENSO-Neutral / La Nina %
for the next 9 overlapping 3-month seasons) from the official page's HTML table.

D14: the ENSO-STATE forecast is a global driver-index forecast (not a Kenya weather forecast) ->
allowed. IRI stopped serving forecast data (2025); CPC RONI probabilities are now the official
source, and RONI matches the observed index we already carry (enso_drivers_seasonal). Values are
parsed from the source HTML table (header-keyed regex), none typed by a model; each row is gated to sum ~100%.

Hardened against column swaps (V2-68c):
  Dynamically inspects the table header (<th scope="col">) to map column positions to phase names
  (La Niña, Neutral, El Niño) rather than assuming fixed positional indices. Aborts immediately
  if headers are missing, renamed, or ambiguous.

This forecast REFRESHES monthly -- re-run to update. Emits:
  enso_state_probabilities.parquet  [season, la_nina, neutral, el_nino, issued, source_url]

Usage:  python3 enso_state_prob_build.py
"""
import datetime, html, json, os, re, shutil, sys
import requests
import pyarrow as pa, pyarrow.parquet as pq

URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/"
OUT = "data/KE-enso-explorer/enso_state_probabilities.parquet"
META = "data/KE-enso-explorer/enso_state_probabilities.meta.json"
SITE_OUT = "_site/data/KE-enso-explorer/enso_state_probabilities.parquet"
SITE_META = "_site/data/KE-enso-explorer/enso_state_probabilities.meta.json"
SEASONS = {"DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"}


def parse_cpc_table(text):
    # 1. Locate the specific probabilities table
    table_m = re.search(r'<table[^>]*id=[\"\']probabilities-table[\"\'][^>]*>(.*?)</table>', text, re.S | re.I)
    if not table_m:
        table_m = re.search(r'<table[^>]*>(?:(?!<table).)*?caption[^>]*>ENSO Probabilities.*?</table>', text, re.S | re.I)
    if not table_m:
        sys.exit("FATAL: Could not locate 'probabilities-table' in CPC HTML markup.")
    table_html = table_m.group(0)

    # 2. Extract header row and dynamically map column names to positions
    header_m = re.search(r'<tr[^>]*class=[\"\']cell-headings[\"\'][^>]*>(.*?)</tr>', table_html, re.S | re.I)
    if not header_m:
        header_m = re.search(r'<tr[^>]*>(.*?)</tr>', table_html, re.S | re.I)
    if not header_m:
        sys.exit("FATAL: Could not find header row in CPC probabilities table.")

    headers_raw = re.findall(r'<th[^>]*>(.*?)</th>', header_m.group(1), re.S | re.I)
    headers = [re.sub(r'<[^>]+>', '', html.unescape(h)).strip() for h in headers_raw]
    if not headers:
        sys.exit("FATAL: Header row contained no <th> cells.")

    col_map = {}
    for idx, h in enumerate(headers):
        hl = h.lower()
        if "season" in hl:
            col_map["season"] = idx
        elif "la ni" in hl:
            col_map["la_nina"] = idx
        elif "neutral" in hl:
            col_map["neutral"] = idx
        elif "el ni" in hl:
            col_map["el_nino"] = idx

    # Gate: all 4 required columns must be explicitly identified in the header
    required_cols = ["season", "la_nina", "neutral", "el_nino"]
    missing_cols = [c for c in required_cols if c not in col_map]
    if missing_cols:
        sys.exit(f"FATAL: Missing expected column headers in table: {missing_cols}. Found: {headers}")

    print(f"Verified CPC Table Headers: {headers}")
    print(f"Dynamic Column Map: {col_map}")

    # Calculate td index offsets (the season header is a <th>, while probabilities are <td> cells)
    sea_col_idx = col_map["season"]
    td_map = {
        "la_nina": col_map["la_nina"] - 1 if col_map["la_nina"] > sea_col_idx else col_map["la_nina"],
        "neutral": col_map["neutral"] - 1 if col_map["neutral"] > sea_col_idx else col_map["neutral"],
        "el_nino": col_map["el_nino"] - 1 if col_map["el_nino"] > sea_col_idx else col_map["el_nino"]
    }

    # 3. Extract issued date
    m_issued = re.search(r"Issued\s+([A-Z][a-z]+\s+\d{4})", re.sub(r"<[^>]+>", " ", text))
    issued = m_issued.group(1) if m_issued else None
    if not issued:
        print("WARNING: Could not parse 'Issued [Month YYYY]' from page text.")

    # 4. Extract data rows
    rows, seen = [], set()
    row_matches = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S | re.I)
    for r_html in row_matches:
        if "cell-headings" in r_html or "<th scope=\"col\"" in r_html:
            continue
        sea_m = re.search(r'<abbr[^>]*>\s*([A-Z]{3})\b', r_html)
        if not sea_m:
            continue
        sea = sea_m.group(1)
        if sea not in SEASONS or sea in seen:
            continue

        tds = re.findall(r'<td[^>]*>\s*(\d+)\s*</td>', r_html)
        if len(tds) < 3:
            sys.exit(f"FATAL: Row {sea} contains fewer than 3 probability cells: {tds}")

        ln = int(tds[td_map["la_nina"]])
        ne = int(tds[td_map["neutral"]])
        en = int(tds[td_map["el_nino"]])

        # Gate: probabilities must sum to ~100%
        prob_sum = ln + ne + en
        if not (97 <= prob_sum <= 103):
            sys.exit(f"FATAL: Row {sea} probabilities sum to {prob_sum}% (LN:{ln} NE:{ne} EN:{en}), not ~100%")

        seen.add(sea)
        rows.append({
            "season": sea,
            "la_nina": ln,
            "neutral": ne,
            "el_nino": en,
            "issued": issued,
            "source_url": URL
        })

    if len(rows) < 6:
        sys.exit(f"FATAL: Only {len(rows)} seasons parsed from table. Expected at least 6 (standard 9).")

    return rows, issued


def update_metadata(today_iso):
    for meta_path in [META, SITE_META]:
        if not os.path.exists(meta_path):
            continue
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["fetched_on"] = today_iso
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"Updated metadata fetched_on to {today_iso} in {meta_path}")
        except Exception as e:
            print(f"Notice: Failed to update {meta_path}: {e}")


def main():
    print(f"Fetching live CPC ENSO probabilities from {URL}...")
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()

    rows, issued = parse_cpc_table(resp.text)
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, OUT)
    print(f"Successfully wrote {len(rows)} forecast rows to {OUT}")

    if os.path.exists(os.path.dirname(SITE_OUT)):
        pq.write_table(table, SITE_OUT)
        print(f"Synchronized parquet to {SITE_OUT}")

    today_iso = datetime.date.today().isoformat()
    update_metadata(today_iso)

    print(f"\nIssued: {issued} | Season Count: {len(rows)}")
    for r in rows:
        print(f"  {r['season']}: El Niño {r['el_nino']:>3}%  |  Neutral {r['neutral']:>3}%  |  La Niña {r['la_nina']:>3}%")


if __name__ == "__main__":
    main()
