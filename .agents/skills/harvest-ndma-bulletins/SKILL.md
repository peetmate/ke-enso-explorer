---
name: harvest-ndma-bulletins
description: Harvest the index of Kenya NDMA drought early warning bulletins from the KnowledgeWeb document library (knowledgeweb.ndma.go.ke) into the ENSO-explorer parquet. Use when refreshing the bulletin index, adding a bulletin category (Long/Short Rain Assessments), or when the harvest breaks after an NDMA site change. Covers the DevExpress grid-state callback that paging depends on, and every trap in the library's metadata.
metadata:
  type: extractor
---

# harvest-ndma-bulletins — NDMA KnowledgeWeb document index

Build `data/KE-enso-explorer/ndma_bulletin_index.parquet` — an inventory of every NDMA drought
early warning bulletin, keyed on `doc_uuid`. **Index only**: no bulletin PDF is downloaded and no
indicator value is extracted. Those belong to a later phase, in a separate parquet joined on
`doc_uuid`.

Engine: `data/KE-enso-explorer/_sources/ndma_index_build.py`.
Run with `/Users/pstewarda/miniforge3/bin/python3` (needs `requests`, `pandas`, `pyarrow`,
`cryptography`).

## Source

- `https://knowledgeweb.ndma.go.ke/Public/Resources/Default.aspx?ID=<n>` — ASP.NET WebForms
  driving a DevExpress `ASPxGridView`. Categories: **7** National DEW bulletins,
  **11** County DEW bulletins. On 2026-11-19 the first pages reported 108 and 3,412 listings;
  these are observations, not permanent gate constants. Also 16/17 Long Rain Assessments, 18/19 Short Rain
  Assessments — `secondary`, off by default. IDs 9/12/13 are the *unfiltered whole library*
  (4,141), not distinct categories; harvesting them duplicates everything.
- PDF for any row: `https://knowledgeweb.ndma.go.ke/Library/doclink.aspx?document=<uuid>` —
  the **same uuid** as the grid's `ResourceDetails.aspx?doc=<uuid>`.
- No `robots.txt`, no `sitemap.xml`, no RSS. The grid is the only enumeration route.

## Why the naive approach fails

`&page=2`, `&pageIndex=1`, `&Page=2` are **silently ignored** and return page 1. There is no GET
paging. The raw PDF filename carries an unguessable upload timestamp
(`Garissa_County_DEW_Bulletin_Jan_2026` **`20260217200643`** `.pdf`), so filenames are useless for
enumeration too — and county/date must come from the **grid**, not the filename.

## The key: a hidden field that is not in the HTML

Paging is a callback POST whose load-bearing part is a hidden form field DevExpress creates
**client-side**, so it never appears in the served markup:

```js
GetStateHiddenFieldName: function() { return this.uniqueID; }   // ctl00$ContentPlaceHolder1$docGrid
```

Post the callback without it and the server rebinds an **empty grid** and returns a ~10 KB stub
with zero rows — HTTP 200, no error, nothing to indicate you got nothing. That single fact is what
makes this site look unscrapeable.

Its value *is* in the HTML, inside the `ASPx.createControl(ASPxClientGridView, …)` script block:

```
'stateObject':{'keys':['6272',…],'callbackState':'BNgB0nnXvkl…'}
```

Round-trip it and `PN<n>` gives **random access** to any page — no sequential walk, no
callbackState chaining, and `__VIEWSTATE` is unchanged across callbacks (parse it once per
category).

```
__CALLBACKID    = ctl00$ContentPlaceHolder1$docGrid     # uniqueID, NOT the clientID
__CALLBACKPARAM = c0:KV|<len>;<json keys>;GB|<len>;12|PAGERONCLICK3|PN<0-based page>;
<uniqueID>      = {"keys":[…],"callbackState":"…","groupLevelState":{},"selection":""}
```

`ContentPlaceHolder1_docGrid` (the clientID) as `__CALLBACKID` returns
`"The target … did not implement ICallbackEventHandler"`. Use the uniqueID.

## The validation gate — three invariants, and why row count alone lies

Every response echoes `Page {n+1} of {P} ({N} items)`, checked **per page** so a failure surfaces
on request #2 rather than after 341.

Row count alone is NOT completeness. The first full harvest returned exactly 3410 rows for 3410
reported items — and was still wrong: only **3406 distinct uuids**. So the gate asserts three
things:

1. **Row completeness** — every sweep enumerates exactly `items_reported` rows.
2. **Duplicate accounting** — `uuids_unique + duplicate_listings == items_reported`. NDMA lists
   four county documents **twice**, at widely separated offsets, with the same grid key and title.
   That is a property of their library, and it must reconcile rather than be hidden.
3. **Closure** — a second sweep under a **different column sort** surfaces **zero** new documents.
   This is what actually rules out offset paging dropping rows, and it is the only one of the
   three that can catch that failure.

Plus: `pages_fetched == pages_reported * sweeps` · grid keys unique · `page_echo_mismatches == 0` ·
`pages_with_zero_rows == 0` · every uuid well-formed · `uploaded_before_ref == 0`.

**Do not "fix" a duplicate-uuid failure by deduplicating and moving on** — first prove, with a
differently-ordered sweep, that the duplicates are NDMA's and not yours.

Reported but **not** gating, because blank ≠ zero: unresolved county tokens, unparsed reference
periods, and the count of distinct counties (assert `<= 47`, print the list, **never** assert
`== 47` and never backfill).

## Named gotchas

0. **A second sweep in the SAME order is worthless.** The server's ordering is deterministic:
   an identical sweep returns byte-identical pages (verified against the cache). Only a different
   ORDER redistributes rows across offset windows. `SORT` on **column 3** works; columns 1 and 2
   are silently ignored by the server. A refreshed grid state comes back **unsorted**, so the sort
   must be re-applied after every state refresh or the sweep quietly reverts to natural order.
1. **`Published:` is the UPLOAD date, not the bulletin's reference period.** `Nyeri DEW
   Bulletin-March 2018` → published 2021-12-30; `Turkana DEW Bulletin- July 2014` → published
   2021-12-20. Roughly pages 120-341 are one bulk back-fill done 16-30 Dec 2021. The column is
   named `uploaded_date` precisely so nobody builds a time series on it. The reference period is
   parsed from the **title**.
2. **Parse the period by anchoring on the MONTH token**, taking the 4-digit year adjacent to it.
   `re.findall(r'\d{4}')[-1]` is right only by luck and breaks on titles carrying two years.
3. **`Document Year` in the grid is sparse** — blank on most back-catalogue rows. Corroboration
   only, never the period.
4. **County is not a column.** The grid's first column is *Category*; county exists only inside
   free-text titles, in many shapes: `Tana_River County Drought EW bulletin_August_ 2026` ·
   `T. Taveta Drought EWS Bulletin Jan 2016` · `Kitui  DEW Bulletin -February 2022` ·
   `Embu (Mbeere) County DEW Bulletin August 2026`. Extend `COUNTY_ALIASES`; leave `county` NULL
   when unresolved and keep `county_raw`. Never invent a spelling — an assert checks every served
   county against `county_key.parquet`.
5. **NDMA is ASAL-only — ~22-23 counties, not 47.** A missing county is structural, never a zero.
6. **`PSP<n>` (page size) is accepted and silently ignored.** You cannot collapse 341 pages into
   35; don't waste time on it.
6b. **Period parsing:** anchor on the month token, and do NOT require a word boundary after it —
   several titles read `August2022`. Where month and year are separated by other words
   (`Samburu June DEW Bulletin - 2023`) the row is labelled `ref_basis=title-month-and-year-apart`
   so it can be audited or excluded. Six titles carry no derivable period at all; they are served
   with `ref_period` NULL, never inferred from `uploaded_date`.
7. **The state-object regex must not anchor on what follows it.** A full page has
   `'stateObject':{…},'callBacksEnabled'`; a callback response has
   `{'id':0,'result':{'stateObject':{…}}}`. Match the opening brace and walk to its partner.
8. **Detail pages add nothing.** `ResourceDetails.aspx?doc=…` yields only Published (same as the
   grid), Author (`NDMA`), Category (same), a download counter, and empty Ref/Source/Description.
   Do not crawl 3,517 of them.
9. **TLS.** The cert lapsed on 2026-09-17 and was renewed with the **same key** by 2026-09-20
   (notAfter 2027-04-04). `SPKI_PIN` is checked every run: a lapse downgrades to `verify=False`
   with a loud banner; a **changed key aborts**. Do not "fix" a pin mismatch by updating the
   constant without verifying out of band.
10. **Rate limiting is deliberate.** 2 s between requests, 3 retries with 5/15/45 s backoff, and
    an immediate abort on 403/429. Responses are cached to `_sources/.ndma_cache/` *before*
    parsing, so a parse bug costs no page refetch. Resume without `--refresh` against the same run's
    cache; live category/state requests may still occur. Never claim zero networking without measuring it.

## Next-run checklist

1. `ndma_index_build.py --selftest` (2 requests) — proves the callback still works.
2. `--only 7` (11 pages) — smoke.
3. Full run into staging with a fresh cache; retain the previous accepted cache and outputs.
   The legacy builder writes outputs before returning a failed gate, so redirect `OUT`, `REPORT_CSV`
   and `CACHE` when importing it, or use an equivalent staged wrapper. Read the validation report,
   require every category served and both closure sweeps passed, compare old/new document UUIDs,
   then promote accepted outputs. **Never hand-edit the parquet.** Allow at least 25 minutes for
   two complete sweeps; preserve the two-second request pacing.
4. Record any newly un-served category in `_sources/ndma_index_ledger.csv` with a reason, using
   the repo status vocabulary (`SERVED, duplicate, secondary, superseded, excluded, out-of-scope,
   held-minor, held-oversum, held-unvalidatable`).
5. Rerun immediately from the same cache without `--refresh`: all cached page bodies must be reused
   and contents identical apart from `harvested_at`. Record actual cache hits and live state requests.
6. `meta_build.py` **from the repo root** (its `OUT` is root-relative), then update `DATA.md`.

## Licence — unresolved, do not assert

NDMA KnowledgeWeb publishes no terms page, no `robots.txt` and no copyright notice. Absence of a
notice is not a licence grant. This index holds **metadata about public documents** plus deep links
back to NDMA's own pages — citation and federation, the weakest-risk end. It is **not** a settled
basis for republishing values extracted from the PDF bodies; settle that before the extraction
phase.
