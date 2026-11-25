#!/usr/bin/env python3
"""Harvest the NDMA KnowledgeWeb bulletin INDEX -> ndma_bulletin_index.parquet.

This builds an inventory of the documents NDMA publishes. It downloads NO bulletin
PDFs and extracts NO indicator values. Those belong to a later phase, in a separate
parquet keyed on `doc_uuid`.

Why this is not a five-line scraper
-----------------------------------
The library is an ASP.NET WebForms page driving a DevExpress ASPxGridView. Paging is
NOT expressible as a GET query string - `&page=2`, `&pageIndex=1` and `&Page=2` are all
silently ignored and return page 1. Paging is a callback POST, and the load-bearing
part of that POST is a hidden form field that NEVER APPEARS IN THE SERVED HTML:
DevExpress creates it client-side (`GetStateHiddenFieldName: () => this.uniqueID`).
Post the callback without it and the server rebinds an empty grid and hands back a
~10 KB stub with zero rows - which looks like a working request and is not.

Its value IS in the HTML, inside the `ASPx.createControl(ASPxClientGridView, ...)`
script block as `'stateObject':{'keys':[...],'callbackState':'...'}`. Round-trip that
and `PN<n>` gives random access to any page.

    __CALLBACKID    = ctl00$ContentPlaceHolder1$docGrid        (uniqueID, NOT the clientID)
    __CALLBACKPARAM = c0:KV|<len>;<json keys>;GB|<len>;12|PAGERONCLICK3|PN<page>;
    <uniqueID>      = {"keys":[...],"callbackState":"...","groupLevelState":{},"selection":""}

Traps this script guards against - all of them observed live, see SKILL.md
-------------------------------------------------------------------------
* `Published:` is the UPLOAD date, not the bulletin's reference period. The 2014-2018
  back-catalogue was bulk-uploaded 16-30 Dec 2021. The column is therefore named
  `uploaded_date`, and the reference period is parsed from the TITLE.
* `Document Year` in the grid is sparse - corroboration only, never the period.
* County is not a grid column (the first column is Category). It lives only inside
  free-text titles, in at least ten different shapes.
* NDMA covers ~22-23 ASAL counties, not 47. A missing county is structural, NEVER zero.
* The TLS certificate lapsed on 2026-09-17 and was renewed (same key) by 2026-09-20.
  The SPKI pin below is checked every run: a lapse downgrades to verify=False with a
  loud banner, but a CHANGED KEY aborts outright.

Usage (from anywhere - paths are self-locating):
    /Users/pstewarda/miniforge3/bin/python3 ndma_index_build.py --selftest
    /Users/pstewarda/miniforge3/bin/python3 ndma_index_build.py --only 7
    /Users/pstewarda/miniforge3/bin/python3 ndma_index_build.py
    /Users/pstewarda/miniforge3/bin/python3 ndma_index_build.py --refresh   # ignore cache
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import json
import math
import re
import socket
import ssl
import sys
import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # only fires on a cert lapse

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "ndma_bulletin_index.parquet"
CACHE = HERE / ".ndma_cache"
COUNTY_KEY = HERE.parent / "county_key.parquet"
REPORT_CSV = HERE / "ndma_index_validation_report.csv"

HOST = "knowledgeweb.ndma.go.ke"
BASE = f"https://{HOST}/Public/Resources/Default.aspx?ID=%d"
DETAIL = f"https://{HOST}/Public/Resources/ResourceDetails.aspx?doc=%s"
PDF = f"https://{HOST}/Library/doclink.aspx?document=%s"
GRID = "ctl00$ContentPlaceHolder1$docGrid"  # uniqueID: __CALLBACKID *and* state field NAME
ROWS_PER_PAGE = 10

# sha256(leaf SubjectPublicKeyInfo, DER), base64. Observed 2026-09-18 on the genuine
# DigiCert/RapidSSL wildcard CN=*.ndma.go.ke, while that cert was one day expired; the
# SAME key was still presented after NDMA renewed (notAfter 2027-04-04, seen 2026-09-20),
# which is what a renewal looks like and a substitution does not. Checked every run.
SPKI_PIN = "2N1ZDcY64PaMVJPQoEMrSFmlNuuix8xie/PzD9pWX+o="

CATEGORIES = {
    7: ("National Drought Early Warning Bulletins", "dew_national", "national"),
    11: ("County Drought Early Warning Bulletins", "dew_county", "county"),
}

DELAY = 2.0
TIMEOUT = 120
RETRY_BACKOFF = (5, 15, 45)
STATE_REFRESH_EVERY = 100  # pages; ASP.NET session default is 20 min
# The library lists 3410 ROWS in the county category but only 3406 DISTINCT documents:
# four documents are listed twice, at widely separated offsets, with the same grid key
# and title (verified 2026-09-27). That is a property of NDMA's data, not of our paging
# - proven by sweeping the grid under two different orderings (natural, and sorted on
# column 3) and finding the SAME 3406 documents and the SAME 4 duplicated uuids.
#
# So the second sweep is a CLOSURE CHECK, not a gap-filler: a different ordering puts
# different rows in each offset window, so if paging were dropping documents the second
# sweep would surface them. It surfaces none. Columns 1 and 2 are not sortable (the
# server ignores them); column 3 is.
SWEEPS = [None, ("3", "ASC")]
UA = ("AdaptationAtlas-KE-ENSO-Explorer/1.0 (bulletin index harvest; "
      "contact p.steward@cgiar.org)")

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], 1)}
MONTHS.update({m[:3].lower(): i for m, i in list(MONTHS.items())})
MONTHS["sept"] = 9

# County spellings as PRINTED in titles -> the county_key.parquet spelling.
# Module-level rename dict, following COUNTY_RENAME in harveststat_build.py:36.
COUNTY_ALIASES = {
    "t. taveta": "Taita Taveta", "t.taveta": "Taita Taveta",
    "taita taveta": "Taita Taveta", "taita-taveta": "Taita Taveta",
    "tana_river": "Tana River", "tana river": "Tana River",
    "tharaka nithi": "Tharaka Nithi", "tharaka-nithi": "Tharaka Nithi",
    "tharaka": "Tharaka Nithi",
    "west pokot": "West Pokot", "w. pokot": "West Pokot", "w.pokot": "West Pokot",
    "elgeyo marakwet": "Elgeyo Marakwet", "e. marakwet": "Elgeyo Marakwet",
    "e/marakwet": "Elgeyo Marakwet", "elgeyo-marakwet": "Elgeyo Marakwet",
    "embu (mbeere)": "Embu", "embu(mbeere)": "Embu", "mbeere": "Embu",
    "embu (mbeere": "Embu", "embu(mbeere": "Embu", "embu mbeere": "Embu",
    "tana-river": "Tana River", "tanariver": "Tana River",
    "west-pokot": "West Pokot", "tharakanithi": "Tharaka Nithi",
    "nyeri (kieni)": "Nyeri", "nyeri (kieni": "Nyeri", "nyeri kieni": "Nyeri",
    "meru north": "Meru", "meru central": "Meru", "meru south": "Meru",
    "homabay": "Homa Bay", "homa bay": "Homa Bay",
    "muranga": "Murang'a", "murang'a": "Murang'a",
    "trans nzoia": "Trans Nzoia", "uasin gishu": "Uasin Gishu",
    "nairobi city": "Nairobi", "makueni": "Makueni",
}

# Everything before one of these in a title is the county token.
COUNTY_STOP = re.compile(
    r"\b(county|counties|dew|drought|ews|ew\b|bulletin|early\s+warning)", re.I)


# --------------------------------------------------------------------- TLS pin

def spki_fingerprint(host: str, port: int = 443) -> tuple[str, str]:
    """Return (base64 sha256 of the leaf SPKI, notAfter string). No verification."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    import base64

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=30) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    cert = x509.load_der_x509_certificate(der)
    spki = cert.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo)
    pin = base64.b64encode(hashlib.sha256(spki).digest()).decode()
    not_after = cert.not_valid_after_utc.isoformat()
    return pin, not_after


def check_tls() -> str:
    """Abort on a substituted certificate. Returns TLS-OK / TLS-EXPIRED."""
    pin, not_after = spki_fingerprint(HOST)
    expired = dt.datetime.fromisoformat(not_after) < dt.datetime.now(dt.timezone.utc)
    if pin != SPKI_PIN:
        sys.exit(
            f"ABORT: TLS public-key pin mismatch for {HOST}.\n"
            f"  expected {SPKI_PIN}\n  observed {pin}\n"
            f"  The certificate has been SUBSTITUTED, or NDMA has legitimately rotated "
            f"its key. Verify out of band before updating SPKI_PIN.")
    if expired:
        print("!" * 78)
        print(f"! {HOST} TLS certificate EXPIRED {not_after}.")
        print("! Falling back to verify=False. The SPKI pin matched, so the key is")
        print("! unchanged from the one observed on 2026-09-18 - a lapse, not a swap.")
        print("!" * 78)
        return "TLS-EXPIRED"
    print(f"TLS: certificate valid (notAfter {not_after}), SPKI pin matched - "
          f"verifying the full chain.")
    return "TLS-OK"


# ------------------------------------------------------------------ grid state

def form_value(page_html: str, name: str) -> str:
    m = re.search(r'name="%s"[^>]*value="([^"]*)"' % re.escape(name), page_html)
    return m.group(1) if m else ""


def grid_state(page_html: str) -> tuple[list[str], str]:
    """Pull the client-generated grid state out of a page OR a callback response.

    The two differ: the full page has `'stateObject':{...},'callBacksEnabled':...`,
    while a callback response has `{'id':0,'result':{'stateObject':{...}}}`. Anchoring
    on what follows the object therefore breaks on callbacks, so match the opening
    brace and walk to its partner instead.
    """
    i = page_html.find("'stateObject':")
    assert i >= 0, ("grid stateObject not found - DevExpress markup changed. "
                    "Paging cannot work without it; see the module docstring.")
    j = page_html.index("{", i)
    depth, end = 0, None
    for k in range(j, min(len(page_html), j + 20000)):
        if page_html[k] == "{":
            depth += 1
        elif page_html[k] == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    assert end, "stateObject braces unbalanced"
    so = page_html[j:end]
    km = re.search(r"'keys':\[([^\]]*)\]", so)
    cm = re.search(r"'callbackState':'([^']*)'", so)
    assert cm, "callbackState missing from stateObject"
    keys = ([k.strip().strip("'\"") for k in km.group(1).split(",")]
            if km and km.group(1).strip() else [])
    return keys, cm.group(1)


def callback_param(keys: list[str], arg: str) -> str:
    kv = json.dumps(keys, separators=(",", ":"))
    gb = "".join(f"{len(a)}|{a}" for a in ["PAGERONCLICK", arg])
    return f"c0:KV|{len(kv)};{kv};GB|{len(gb)};{gb};"


# ------------------------------------------------------------------ http layer

class Harvester:
    def __init__(self, refresh: bool = False, verify: bool = True):
        self.s = requests.Session()
        # Full chain verification whenever the certificate is valid. It lapsed once
        # (2026-09-17) and was renewed with the SAME key by 2026-09-20; verify=False is
        # a fallback for a repeat lapse, never the default.
        self.s.verify = verify
        self.s.headers.update({"User-Agent": UA})
        self.refresh = refresh
        self.net = 0
        self.cache_hits = 0
        CACHE.mkdir(exist_ok=True)

    def _sleep(self):
        time.sleep(DELAY)

    def _request(self, fn, what: str) -> str:
        for attempt, backoff in enumerate((0,) + RETRY_BACKOFF):
            if backoff:
                print(f"    retry {attempt} for {what} in {backoff}s")
                time.sleep(backoff)
            try:
                r = fn()
            except requests.RequestException as exc:
                if attempt == len(RETRY_BACKOFF):
                    sys.exit(f"ABORT: {what} failed after retries: {exc}")
                continue
            if r.status_code in (403, 429):
                sys.exit(f"ABORT: {what} returned HTTP {r.status_code}. "
                         f"Stopping rather than hammering the server.")
            if r.status_code >= 500:
                if attempt == len(RETRY_BACKOFF):
                    sys.exit(f"ABORT: {what} returned HTTP {r.status_code} after retries")
                continue
            r.raise_for_status()
            self.net += 1
            return r.text
        raise AssertionError("unreachable")

    def category_page(self, cat: int) -> str:
        url = BASE % cat
        self._sleep()
        return self._request(lambda: self.s.get(url, timeout=TIMEOUT), f"GET ID={cat}")

    def sort(self, cat: int, col: str, order: str, keys: list[str], cbs: str,
             vs: str, vsg: str, ev: str, pass_idx: int) -> str:
        """Apply a column sort. The response IS page 1 of the new ordering."""
        cf = CACHE / f"pass{pass_idx}"
        cf.mkdir(parents=True, exist_ok=True)
        cf = cf / f"ID{cat}_sort.html"
        if cf.exists() and not self.refresh:
            self.cache_hits += 1
            return cf.read_text()
        url = BASE % cat
        gb = "".join(f"{len(a)}|{a}" for a in ["SORT", col, "", order, "true"])
        kv = json.dumps(keys, separators=(",", ":"))
        data = {
            "__EVENTTARGET": "", "__EVENTARGUMENT": "",
            "__VIEWSTATE": vs, "__VIEWSTATEGENERATOR": vsg, "__EVENTVALIDATION": ev,
            "__CALLBACKID": GRID,
            "__CALLBACKPARAM": f"c0:KV|{len(kv)};{kv};GB|{len(gb)};{gb};",
            GRID: json.dumps({"keys": keys, "callbackState": cbs,
                              "groupLevelState": {}, "selection": ""},
                             separators=(",", ":")),
        }
        self._sleep()
        body = self._request(
            lambda: self.s.post(url, data=data, timeout=TIMEOUT,
                                headers={"X-Requested-With": "XMLHttpRequest",
                                         "Referer": url}),
            f"ID={cat} sort col{col} {order}")
        cf.write_text(body)
        return body

    def page(self, cat: int, page: int, keys: list[str], cbs: str,
             vs: str, vsg: str, ev: str, pass_idx: int = 0) -> str:
        """Fetch one grid page (0-based). Cached to disk; cache IS the resume mechanism."""
        pd_ = CACHE / f"pass{pass_idx}"
        pd_.mkdir(parents=True, exist_ok=True)
        cf = pd_ / f"ID{cat}_p{page:04d}.html"
        if cf.exists() and not self.refresh:
            self.cache_hits += 1
            return cf.read_text()
        url = BASE % cat
        data = {
            "__EVENTTARGET": "", "__EVENTARGUMENT": "",
            "__VIEWSTATE": vs, "__VIEWSTATEGENERATOR": vsg, "__EVENTVALIDATION": ev,
            "__CALLBACKID": GRID,
            "__CALLBACKPARAM": callback_param(keys, f"PN{page}"),
            GRID: json.dumps({"keys": keys, "callbackState": cbs,
                              "groupLevelState": {}, "selection": ""},
                             separators=(",", ":")),
        }
        self._sleep()
        body = self._request(
            lambda: self.s.post(url, data=data, timeout=TIMEOUT,
                                headers={"X-Requested-With": "XMLHttpRequest",
                                         "Referer": url}),
            f"ID={cat} pass {pass_idx} page {page}")
        cf.write_text(body)  # write BEFORE parsing, so a parse bug costs no refetch
        return body


# --------------------------------------------------------------------- parsing

ECHO = re.compile(r"Page (\d+) of (\d+) \(([\d,]+) items\)")
ROW = re.compile(
    r'href="ResourceDetails\.aspx\?doc=([0-9a-fA-F-]{36})"[^>]*>(.*?)</a>', re.S)


def page_echo(body: str) -> tuple[int, int, int] | None:
    """The server states its own position and total. Our completeness proof."""
    m = ECHO.search(html.unescape(body))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3).replace(",", ""))


def parse_rows(body: str) -> list[dict]:
    t = html.unescape(body)
    out = []
    for m in ROW.finditer(t):
        uuid = m.group(1).lower()
        title = re.sub(r"<[^>]+>", "", m.group(2))
        title = re.sub(r"\s+", " ", title).strip()
        tail = t[m.end():m.end() + 900]
        pm = re.search(r"Published:\s*([A-Za-z]+)\s+(\d{4})", tail)
        dm = re.search(r'title="Published:\s*(\d{4}-\d{2}-\d{2})', tail)
        out.append({
            "doc_uuid": uuid,
            "title_raw": title,
            "uploaded_label": f"Published: {pm.group(1)} {pm.group(2)}" if pm else None,
            "uploaded_date": dm.group(1) if dm else None,
        })
    return out


def parse_period(title: str) -> tuple[int | None, int | None, str]:
    """Reference period from the TITLE. Never from the upload date.

    Anchors on the MONTH token and takes the 4-digit year adjacent to it. A blind
    `findall(r'\\d{4}')[-1]` would be right only by luck on titles carrying two years.
    """
    t = re.sub(r"[_\-]+", " ", title)
    t = re.sub(r"\s+", " ", t).strip()
    names = "|".join(sorted(MONTHS, key=len, reverse=True))
    # No trailing \b after the month: "August2022" has no word boundary before the
    # digits, and several titles are written exactly that way.
    m = re.search(rf"\b({names})[\s,./-]*((?:19|20)\d{{2}})\b", t, re.I)
    if m:
        return int(m.group(2)), MONTHS[m.group(1).lower()], "title-month-year"
    m = re.search(rf"\b((?:19|20)\d{{2}})[\s,./-]*({names})\b", t, re.I)
    if m:
        return int(m.group(1)), MONTHS[m.group(2).lower()], "title-month-year"
    # Month and year both present but separated by other words, e.g.
    # "Samburu June DEW Bulletin - 2023". Both tokens are in the title, so this is
    # still extraction rather than inference - but it is a weaker basis and is
    # labelled separately so it can be audited or excluded.
    my = re.search(rf"\b({names})\b", t, re.I)
    yy = re.search(r"\b((?:19|20)\d{2})\b", t)
    if my and yy:
        return int(yy.group(1)), MONTHS[my.group(1).lower()], "title-month-and-year-apart"
    if yy:
        return int(yy.group(1)), None, "title-year-only"
    return None, None, "unparsed"


def parse_county(title: str, valid: set[str]) -> tuple[str | None, str | None]:
    """Return (county_raw, county_resolved). Resolved is NULL when unknown - never guessed."""
    t = re.sub(r"[_]+", " ", title)
    t = re.sub(r"\s+", " ", t).strip()
    m = COUNTY_STOP.search(t)
    raw = (t[:m.start()] if m else t).strip(" -,.:;")
    # Some titles put the period BEFORE the stop word ("Samburu June 2019 DEW
    # Bulletin"), which would otherwise leave "Samburu June" as the county token.
    # Strip a trailing year and/or month name; this removes no county name.
    names = "|".join(sorted(MONTHS, key=len, reverse=True))
    raw = re.sub(rf"\s*\b(?:{names})\b\s*((?:19|20)\d{{2}})?\s*$", "", raw, flags=re.I)
    raw = re.sub(r"\s*\b(?:19|20)\d{2}\b\s*$", "", raw).strip(" -,.:;(")
    if not raw:
        return None, None
    key = raw.lower().strip(" -,.:;(")
    if key in COUNTY_ALIASES:
        return raw, COUNTY_ALIASES[key]
    for v in valid:
        if key == v.lower():
            return raw, v
    return raw, None


# ----------------------------------------------------------------------- gates

def gate(rep: dict) -> bool:
    """Pure function over the report dict (napr_build.py:167-201 shape)."""
    sweeps = [int(x) for x in rep["sweep_rows"].split(";") if x]
    return (
        # 1. ROW completeness: every sweep enumerated exactly the number of rows the
        #    SITE itself reports. Checked per page via the server's own page echo.
        bool(sweeps) and all(n == rep["items_reported"] for n in sweeps)
        # 2. DUPLICATE accounting: distinct documents + NDMA's own repeated listings
        #    add back up to the row count. NDMA lists some documents twice; that is a
        #    property of their library, and it must reconcile rather than be hidden.
        and rep["uuids_unique"] + rep["duplicate_listings"] == rep["items_reported"]
        and rep["rows_parsed"] == rep["uuids_unique"]
        # 3. CLOSURE: a second, differently-ordered sweep surfaced no new document.
        #    This is what rules out offset paging silently dropping rows.
        and rep["closure_new_docs"] == 0
        and rep["pages_reported"] == math.ceil(rep["items_reported"] / ROWS_PER_PAGE)
        and rep["pages_fetched"] == rep["pages_reported"] * rep["passes_used"]
        and rep["keys_unique"] == rep["rows_parsed"]
        and rep["page_echo_mismatches"] == 0
        and rep["pages_with_zero_rows"] == 0
        and rep["uuid_malformed"] == 0
        and rep["uploaded_before_ref"] == 0
    )


def validation_label(rep: dict) -> str:
    if not gate(rep):
        bad = []
        sweeps = [int(x) for x in rep["sweep_rows"].split(";") if x]
        if not sweeps or any(n != rep["items_reported"] for n in sweeps):
            bad.append(f"sweep row counts {sweeps} != site count {rep['items_reported']}")
        if rep["uuids_unique"] + rep["duplicate_listings"] != rep["items_reported"]:
            bad.append(f"{rep['uuids_unique']} distinct + {rep['duplicate_listings']} "
                       f"duplicate listings != {rep['items_reported']} rows")
        if rep["closure_new_docs"] != 0:
            bad.append(f"closure check failed: a second ordering found "
                       f"{rep['closure_new_docs']} document(s) the first sweep missed")
        if rep["page_echo_mismatches"]:
            bad.append(f"{rep['page_echo_mismatches']} page-echo mismatches")
        if rep["pages_with_zero_rows"]:
            bad.append(f"{rep['pages_with_zero_rows']} empty pages (grid state rejected)")
        if rep["keys_unique"] != rep["rows_parsed"]:
            bad.append("grid keys not unique across the union")
        if rep["uploaded_before_ref"]:
            bad.append(f"{rep['uploaded_before_ref']} rows uploaded before their reference month")
        return "HELD: " + "; ".join(bad or ["gate failed"])
    return (f"{rep['items_reported']} rows enumerated per sweep (server-echoed page "
            f"number checked on every page) = {rep['uuids_unique']} distinct documents "
            f"+ {rep['duplicate_listings']} listed twice by NDMA; closure confirmed by a "
            f"second sweep under a different sort finding 0 new documents")


# ------------------------------------------------------------------ harvest one

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _one_pass(h: Harvester, cat: int, max_pages: int | None,
              pass_idx: int, sort: tuple[str, str] | None = None
              ) -> tuple[list[dict], dict]:
    """One full sweep of a category, optionally under a column sort."""
    cat_body = h.category_page(cat)

    assert GRID.split("$")[-1] in cat_body, "grid control id changed"
    keys, cbs = grid_state(cat_body)
    vs, vsg, ev = (form_value(cat_body, "__VIEWSTATE"),
                   form_value(cat_body, "__VIEWSTATEGENERATOR"),
                   form_value(cat_body, "__EVENTVALIDATION"))
    assert vs, "__VIEWSTATE missing"

    if sort:
        body = h.sort(cat, sort[0], sort[1], keys, cbs, vs, vsg, ev, pass_idx)
        keys, cbs = grid_state(body)
        assert parse_rows(body), (
            f"sort col{sort[0]} {sort[1]} returned no rows - the sort command was "
            f"rejected; do not treat this sweep as a different ordering")
    else:
        body = cat_body

    echo = page_echo(body)
    assert echo, "pager echo not found on the category page"
    _, pages_reported, items_reported = echo

    n_pages = pages_reported if max_pages is None else min(max_pages, pages_reported)
    rows, echo_bad, zero_pages, first_uuids = [], 0, 0, []

    for pg in range(n_pages):
        if pg and pg % STATE_REFRESH_EVERY == 0:
            cat_body = h.category_page(cat)
            keys, cbs = grid_state(cat_body)
            vs, vsg, ev = (form_value(cat_body, "__VIEWSTATE"),
                           form_value(cat_body, "__VIEWSTATEGENERATOR"),
                           form_value(cat_body, "__EVENTVALIDATION"))
            if sort:  # a refreshed state is UNSORTED - re-apply, or the sweep reverts
                sb = h.sort(cat, sort[0], sort[1], keys, cbs, vs, vsg, ev, pass_idx)
                keys, cbs = grid_state(sb)

        pb = body if pg == 0 else h.page(cat, pg, keys, cbs, vs, vsg, ev, pass_idx)
        pr = parse_rows(pb)

        if not pr and pg > 0:
            # Signature of a rejected grid-state field / expired session. One retry.
            print(f"    page {pg}: zero rows - refreshing state, retrying once")
            body = h.category_page(cat)
            keys, cbs = grid_state(body)
            vs, vsg, ev = (form_value(body, "__VIEWSTATE"),
                           form_value(body, "__VIEWSTATEGENERATOR"),
                           form_value(body, "__EVENTVALIDATION"))
            (CACHE / f"pass{pass_idx}" / f"ID{cat}_p{pg:04d}.html").unlink(missing_ok=True)
            pb = h.page(cat, pg, keys, cbs, vs, vsg, ev, pass_idx)
            pr = parse_rows(pb)
            if not pr:
                zero_pages += 1
                sys.exit(f"ABORT: ID={cat} page {pg} returned no rows twice.\n"
                         f"  first 500 bytes: {pb[:500]!r}")

        e = page_echo(pb)
        if not e or e[0] != pg + 1:
            echo_bad += 1
            sys.exit(f"ABORT: ID={cat} requested page {pg} but server echoed "
                     f"{e[0] if e else 'nothing'}. Paging is not moving; "
                     f"do not trust this harvest.")

        if pr:
            first_uuids.append(pr[0]["doc_uuid"])
        pkeys = grid_state(pb)[0] if pg else keys
        for i, r in enumerate(pr):
            r.update({"page_index": pg, "row_index": i,
                      "grid_key": pkeys[i] if i < len(pkeys) else None})
        rows += pr
        if pg % 50 == 0 or pg == n_pages - 1:
            print(f"    page {pg + 1}/{n_pages}  rows={len(rows)}")

    stats = {
        "pages_reported": pages_reported, "items_reported": items_reported,
        "pages_fetched": n_pages, "rows_seen": len(rows),
        "zero_pages": zero_pages, "echo_bad": echo_bad,
        "first_uuid_repeats": sum(1 for a, b in zip(first_uuids, first_uuids[1:]) if a == b),
    }
    return rows, stats


def harvest(h: Harvester, cat: int, valid: set[str], max_pages: int | None,
            harvested_at: str) -> tuple[list[dict], dict]:
    """Harvest a category to completeness.

    The grid pages with OFFSET over a non-unique sort, so one sweep can repeat a
    document and silently drop another. Additional sweeps shuffle differently, so the
    UNION converges on the full set. The stopping condition is the site's own item
    count - we never guess that we are done.
    """
    label, series, scope = CATEGORIES[cat]
    print(f"\n=== ID={cat}  {label} ===")

    by_uuid: dict[str, dict] = {}
    items_reported = pages_reported = pages_fetched = 0
    zero_pages = echo_bad = repeats = rows_seen = 0
    passes_used = 0
    sweep_rows: list[int] = []      # rows enumerated per sweep; each must equal the site count
    dup_uuids: set[str] = set()
    closure_new = None              # documents the SECOND ordering found that the first missed

    for pass_idx, sort in enumerate(SWEEPS):
        passes_used = pass_idx + 1
        order = "natural order" if not sort else f"sort col{sort[0]} {sort[1]}"
        print(f"  sweep {passes_used} ({order}):")
        rows, st = _one_pass(h, cat, max_pages, pass_idx, sort)
        items_reported, pages_reported = st["items_reported"], st["pages_reported"]
        pages_fetched += st["pages_fetched"]
        rows_seen += st["rows_seen"]
        sweep_rows.append(st["rows_seen"])
        zero_pages += st["zero_pages"]
        echo_bad += st["echo_bad"]
        repeats += st["first_uuid_repeats"]

        seen = collections.Counter(r["doc_uuid"] for r in rows)
        dup_uuids |= {u for u, n in seen.items() if n > 1}
        new = 0
        for r in rows:
            if r["doc_uuid"] not in by_uuid:
                by_uuid[r["doc_uuid"]] = r
                new += 1
        if pass_idx == 0:
            print(f"    {st['rows_seen']} rows -> {len(seen)} distinct documents "
                  f"({st['rows_seen'] - len(seen)} listed twice by NDMA)")
        else:
            closure_new = new
            print(f"    closure check: a different ordering surfaced {new} new document(s)"
                  f" - {'PASS, the set is closed' if new == 0 else 'FAIL, paging is dropping rows'}")
        if max_pages is not None:
            break  # a truncated smoke run cannot prove closure

    rows = list(by_uuid.values())
    for r in rows:
        r.update({"category": label, "category_id": cat, "series": series, "scope": scope})
        y, m, basis = parse_period(r["title_raw"])
        r["ref_year"], r["ref_month"], r["ref_basis"] = y, m, basis
        r["ref_period"] = (f"{y:04d}-{m:02d}" if y and m else (f"{y:04d}" if y else None))
        if scope == "county":
            r["county_raw"], r["county"] = parse_county(r["title_raw"], valid)
        else:
            r["county_raw"], r["county"] = None, None
        r["detail_url"] = DETAIL % r["doc_uuid"]
        r["pdf_url"] = PDF % r["doc_uuid"]
        r["harvested_at"] = harvested_at
        r["doc_year_grid"] = None

    before = 0
    for r in rows:
        if r["uploaded_date"] and r["ref_year"] and r["ref_month"]:
            up = dt.date.fromisoformat(r["uploaded_date"])
            if (r["ref_year"], r["ref_month"]) > (up.year, up.month):
                before += 1

    rep = {
        "category_id": cat, "category": label, "series": series,
        "items_reported": items_reported, "pages_reported": pages_reported,
        "sweep_rows": ";".join(str(x) for x in sweep_rows),
        "duplicate_listings": items_reported - len(by_uuid),
        "duplicate_uuids": ";".join(sorted(dup_uuids)),
        "closure_new_docs": closure_new if closure_new is not None else -1,
        "passes_used": passes_used, "pages_fetched": pages_fetched,
        "rows_seen": rows_seen, "rows_parsed": len(rows),
        "uuids_unique": len({r["doc_uuid"] for r in rows}),
        "keys_unique": len({r["grid_key"] for r in rows if r["grid_key"]}),
        "pages_with_zero_rows": zero_pages,
        "first_uuid_repeats": repeats,
        "page_echo_mismatches": echo_bad,
        "uuid_malformed": sum(1 for r in rows if not UUID_RE.match(r["doc_uuid"])),
        "uploaded_before_ref": before,
        "ref_period_unparsed": sum(1 for r in rows if r["ref_basis"] == "unparsed"),
        "county_unresolved": sum(1 for r in rows if r["scope"] == "county" and not r["county"]),
    }
    return rows, rep


# ---------------------------------------------------------------------- output

SCHEMA = pa.schema([
    ("doc_uuid", pa.string()), ("grid_key", pa.string()),
    ("category", pa.string()), ("category_id", pa.int32()),
    ("series", pa.string()), ("scope", pa.string()),
    ("title_raw", pa.string()), ("county_raw", pa.string()), ("county", pa.string()),
    ("gaul1_code", pa.float64()),
    ("ref_year", pa.int32()), ("ref_month", pa.int32()),
    ("ref_period", pa.string()), ("ref_basis", pa.string()),
    ("doc_year_grid", pa.int32()),
    ("uploaded_date", pa.date32()), ("uploaded_label", pa.string()),
    ("detail_url", pa.string()), ("pdf_url", pa.string()),
    ("page_index", pa.int32()), ("row_index", pa.int32()),
    ("harvested_at", pa.string()),
])


def write_outputs(rows: list[dict], reports: list[dict], ckey: pd.DataFrame,
                  harvested_at: str, tls: str, h: Harvester):
    df = pd.DataFrame(rows)
    df = df.merge(ckey, on="county", how="left")
    df["uploaded_date"] = pd.to_datetime(df["uploaded_date"], errors="coerce").dt.date
    for c in ("ref_year", "ref_month", "doc_year_grid", "category_id",
              "page_index", "row_index"):
        df[c] = df[c].astype("Int32")
    df = df.sort_values(["series", "county", "ref_year", "ref_month", "doc_uuid"],
                        na_position="last").reset_index(drop=True)
    df = df[[f.name for f in SCHEMA]]
    pq.write_table(pa.Table.from_pandas(df, schema=SCHEMA, preserve_index=False), OUT)
    print(f"\nwrote {OUT}  ({len(df)} rows)")

    for r in reports:
        r.update({"served": gate(r), "validation": validation_label(r),
                  "tls_verified": tls, "harvested_at": harvested_at,
                  "delay_s": DELAY, "cache_hits": h.cache_hits,
                  "network_requests": h.net})
    with REPORT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(reports[0].keys()))
        w.writeheader()
        w.writerows(reports)
    print(f"wrote {REPORT_CSV}")
    return df


def coverage_report(df: pd.DataFrame):
    print("\n" + "=" * 66)
    print("COVERAGE")
    print("=" * 66)
    for s, g in df.groupby("series"):
        print(f"\n{s}: {len(g)} rows")
        per = g["ref_period"].dropna()
        if len(per):
            print(f"  reference period: {per.min()} -> {per.max()}")
        print(f"  ref_basis: {g['ref_basis'].value_counts().to_dict()}")
        if s == "dew_county":
            res = sorted(g["county"].dropna().unique())
            print(f"  counties resolved: {len(res)} (NDMA is ASAL-only; "
                  f"a missing county is structural, never zero)")
            print(f"    {', '.join(res)}")
            unres = sorted(g.loc[g["county"].isna(), "county_raw"].dropna().unique())
            if unres:
                print(f"  UNRESOLVED county tokens ({len(unres)}) - extend COUNTY_ALIASES:")
                print(f"    {', '.join(unres)}")
    up = pd.to_datetime(df["uploaded_date"], errors="coerce").dt.year.value_counts().sort_index()
    print("\nuploaded_date by year (NOT the reference period - the spike is a bulk back-fill):")
    for y, n in up.items():
        print(f"  {int(y)}: {'#' * min(60, n // 20)} {n}")


# ------------------------------------------------------------------------ main

def selftest(h: Harvester):
    print("selftest: GET ID=7, then callback PN5")
    body = h.category_page(7)
    keys, cbs = grid_state(body)
    vs, vsg, ev = (form_value(body, "__VIEWSTATE"),
                   form_value(body, "__VIEWSTATEGENERATOR"),
                   form_value(body, "__EVENTVALIDATION"))
    print(f"  state: {len(keys)} keys, callbackState {len(cbs)} B, VIEWSTATE {len(vs)} B")
    pb = h.page(7, 5, keys, cbs, vs, vsg, ev)
    e = page_echo(pb)
    rows = parse_rows(pb)
    print(f"  echo={e}  rows={len(rows)}")
    assert e and e[0] == 6, f"expected page 6, got {e}"
    assert len(rows) == ROWS_PER_PAGE, f"expected {ROWS_PER_PAGE} rows, got {len(rows)}"
    print("  SELFTEST PASS - random-access paging works")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", type=int, choices=sorted(CATEGORIES))
    ap.add_argument("--pages", type=int, default=None)
    ap.add_argument("--refresh", action="store_true", help="ignore the disk cache")
    a = ap.parse_args()

    tls = check_tls()
    h = Harvester(refresh=a.refresh, verify=(tls == "TLS-OK"))

    if a.selftest:
        selftest(h)
        return

    ck = pd.read_parquet(COUNTY_KEY)
    valid = set(ck["county"])
    harvested_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    cats = [a.only] if a.only else sorted(CATEGORIES)
    all_rows, reports = [], []
    for cat in cats:
        rows, rep = harvest(h, cat, valid, a.pages, harvested_at)
        all_rows += rows
        reports.append(rep)
        print(f"  gate: {'SERVED' if gate(rep) else 'HELD'} - {validation_label(rep)}")

    df = write_outputs(all_rows, reports, ck, harvested_at, tls, h)

    bad = set(df["county"].dropna()) - valid
    assert not bad, f"invented county spellings not in county_key.parquet: {bad}"
    n_cty = df.loc[df.series == "dew_county", "county"].nunique()
    assert n_cty <= 47, f"{n_cty} counties > 47"

    coverage_report(df)
    print(f"\nnetwork requests={h.net}  cache hits={h.cache_hits}")
    held = [r for r in reports if not r["served"]]
    if held:
        print("\nHELD categories:")
        for r in held:
            print(f"  ID={r['category_id']}: {r['validation']}")
        sys.exit(1)
    print("\nAll categories SERVED.")


if __name__ == "__main__":
    main()
