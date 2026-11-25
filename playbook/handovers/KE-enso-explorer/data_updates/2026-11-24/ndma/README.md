> Archived source-project handover. For this older personal-repository branch, see [port scope and validation](PORT_TO_PERSONAL_SOURCE.md). References below describe the original project environment.

# NDMA index refresh — 24 November 2026

Accepted 3,539 document records, up from 3,516: 22 county and one national October 2026 bulletin, all uploaded on 20 November. This is a document-index refresh only. No bulletin PDFs or indicator values were extracted.

## Delivery states

| State | Result |
| --- | --- |
| Acquisition | Accepted locally: 3,430 county and 109 national documents. |
| Numerical/identity validation | Passed complete two-order enumeration, duplicate reconciliation, retained-ID comparison and cache replay. |
| Metadata | All 22 fields documented; sidecar regenerated; local CDH v0.3.0 record strictly validated. Catalogue submission remains pending. |
| External use | Existing NDMA clearance remains pending. No permission inferred from public access or successful validation. |

## Evidence and limits

- Official sources: [national library](https://knowledgeweb.ndma.go.ke/Public/Resources/Default.aspx?ID=7) and [county library](https://knowledgeweb.ndma.go.ke/Public/Resources/Default.aspx?ID=11).
- National: 109 listings on 11 pages; county: 3,434 listings on 344 pages. Each category was enumerated under natural order and column 3 ascending order. Second order added zero document IDs. Actual page-order differences were also checked.
- Four intrinsic county duplicate listings have exactly the same UUIDs as the previous accepted receipt. No accepted UUID was removed. No changes were found in existing titles, canonical counties, reference periods, upload dates or source links.
- Six unparsed periods and three unresolved county names remain null. Resolved historical coverage remains 23 counties. Twenty-two counties now reach October 2026; Marsabit remains at August 2026 in this library. Missing months remain gaps, not zeros.
- Fresh cache was isolated from the previous run. Harvest used 719 successful HTTP requests and 4 cache hits, excluding the two-request self-test. Immediate replay used 12 live state/count requests and 711 cache hits; table content matched exactly except `harvested_at`. Two-second request pacing and TLS/SPKI checks were preserved.
- Run date is 24 November in America/Bogota; harvest timestamps use UTC (25 November). Upload date and reference month retain distinct meanings.
- Accepted output SHA-256: `947b04dfb590efc2d7b2a751acb309c696aa597c816b46b2ec85eb3e3ed0a0f3`.
- Full acceptance receipt: [`ndma_index_refresh.json`](../../../../../../data/KE-enso-explorer/_sources/ndma_index_refresh.json). [Machine-readable summary](summary.json), [harvest log](harvest.log), [watch result](watch.json), [final platform checks](verification/results.json).

## Reproduction and rollback

Maintained parser and gates: `data/KE-enso-explorer/_sources/ndma_index_build.py`; metadata generator: `_sources/meta_build.py`; catalogue generator: `scripts/build_refresh_catalogue.py`. Exact dated orchestration is saved in [stage_refresh.py](stage_refresh.py), with executed promotion logic in [promote_reviewed.py](promote_reviewed.py). These scripts document this run; the date and paths are deliberately run-specific.

Replay this run from repository root:

```sh
/Users/pstewarda/miniforge3/bin/python3 playbook/handovers/KE-enso-explorer/data_updates/2026-11-24/ndma/stage_refresh.py --stage data/KE-enso-explorer/_sources/.ndma_cache/refresh-20261124 --resume
```

Replay still makes live state requests and requires unchanged publisher counts. For a new edition, follow `.agents/skills/harvest-ndma-bulletins/SKILL.md`: use a new staged cache, redirect builder `OUT`/`REPORT_CSV`/`CACHE`, validate both orders, replay, compare IDs and only then promote. Never reuse this dated receipt as evidence for a later edition.

Raw HTML cache: `data/KE-enso-explorer/_sources/.ndma_cache/refresh-20261124/cache` (ignored); hashes: `_sources/ndma_cache_manifest.json`, with paths relative to the run directory. Prior accepted table and report remain in that run's `before/` directory. Full pre-change file backup: `data/KE-enso-explorer/_sources/.refresh_backups/ndma-20261124`. Restore only NDMA-owned file changes; shared files also contain other sessions' work. Old raw cache remains intact.

## Verification and ownership

Build `303112403`, version `3.15.0`. All seven final platform gates passed, and checked inputs remained unchanged during the run. Final gate results are recorded separately from [initial results](verification-initial/results.json). Initial static/deep checks encountered concurrent catalogue edits: cross-border trade needed its v0.5.0 validator, and a separate ReliefWeb domain correction subsequently appeared. Cross-border provenance was revalidated with its matching schema; NDMA was regenerated separately with pinned v0.3.0 validator revision `b1b0d9a57e82919e417975df3ebef821fedc3f3b`. No unrelated source record or generator edits are included in this task's staged changes.

Global acquisition checks remain incomplete for other assets. NDMA has no technical-handoff issues; its external-use check still records `External-use decision incomplete: ndma`.

Only NDMA changes, dated evidence and this task's build synchronization are staged. No commit, push, pull request, deployment, catalogue submission or provider message. Weekly monitoring now records this accepted edition so the previous availability alert is resolved. No manual action is needed for this index refresh. Bulletin-value extraction would be separate work.
