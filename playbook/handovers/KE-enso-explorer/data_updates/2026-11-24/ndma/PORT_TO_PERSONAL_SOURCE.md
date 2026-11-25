# NDMA-only port to personal source branch — 25 November 2026

This branch ports the accepted NDMA document index from source-project commit `ea9e5d9d6ff325820bfb3ef5a4fc43fc7b47cc08` into `peetmate/ke-enso-explorer:source`, based on `fcbc61ef890be8fe45280cba35407df87c37d6d8`.

The target branch is an older software edition (3.5.1) with only 107 national document records. It now has the exact reviewed 3,539-row Parquet: 3,430 county and 109 national records. All 107 target IDs and their reviewed metadata fields are retained. The target therefore gains 3,432 records. The separately recorded 23 additions describe the latest source-project refresh from its previously accepted 3,516-row edition; these denominators must not be confused.

## Scope and validation

- Parquet bytes match accepted SHA-256 `947b04dfb590efc2d7b2a751acb309c696aa597c816b46b2ec85eb3e3ed0a0f3`.
- All 22 columns and their order match the target schema. UUIDs are unique, counties match the target county key, and target IDs are retained without changes to title, county, reference period, upload date or source links.
- The maintained NDMA harvester is the exact version used for the accepted run. Both order gates pass; deliberately corrupted counts, nonzero closure additions and empty-page reports are rejected.
- Only the NDMA registry entry and field-generation block are added to `meta_build.py`. Regenerating this sidecar produces byte-identical reviewed metadata. Other dataset registry entries are unchanged.
- See [port-validation.json](port-validation.json). Original acquisition/replay evidence and seven passing platform checks remain archived here. They were run in the modern source project, not against this older branch.

This is an isolated data/maintenance port. The target notebook, UI, loaders, release metadata and live `main` branch are unchanged. Data edition identity is recorded by source commit and output hash; the modern source project's build 303112403 is not assigned to the older software edition.

## Maintenance

Follow [the NDMA harvest skill](../../../../../../.agents/skills/harvest-ndma-bulletins/SKILL.md). A refresh must use a new staged cache, both different sort orders and duplicate reconciliation, an immediate replay, and prior-ID comparison before acceptance. The dated `stage_refresh.py` can reproduce the archived run but requires that run's local raw cache and unchanged live counts. `promote_reviewed.py` records promotion in the modern source project; do not run it against this older branch.

Regenerate only this metadata sidecar from the repository root:

```sh
/Users/pstewarda/miniforge3/bin/python3 - <<'PYTHON'
import sys
sys.path.insert(0, 'data/KE-enso-explorer/_sources')
import meta_build
meta_build.D = {'ndma_bulletin_index': meta_build.D['ndma_bulletin_index']}
meta_build.main()
PYTHON
```

## Catalogue, rights and rollback

`source-catalogue.yaml` and `source-catalogue-validation.json` archive the source project's strict local CDH validation. They are not installed into this older branch's provenance or governance system; that integration remains pending. Original readiness reports concern the source project, not this branch. No bulletin PDFs or measurements are included. External-use clearance remains pending; a source-code PR does not establish permission for bulletin-value extraction or redistribution.

Marsabit still ends at August 2026; other missing county/month records remain gaps. No PDF extraction, new upstream harvest, catalogue submission or provider contact occurred during this port.

Rollback: revert this isolated commit, or restore its changed paths from the recorded target base. This PR targets `source`; it is not a merge or deployment to the live `main` branch.
