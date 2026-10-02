# KE-ENSO Explorer — data acquisition & storage manifest

Repeatable record of every dataset powering `notebooks/KE-enso-explorer/notebook.qmd`: where it comes
from, how to re-acquire it, its licence, and where it is stored. Grouped by **source / series** (one
report series = one dataset). Build scripts live in [`_sources/`](./_sources/).

## Storage — three locations
- **Processed parquets** (notebook inputs): here in `data/KE-enso-explorer/*.parquet` — git-versioned,
  public on the branch. **Canonical.**
- **Build/extract scripts**: `data/KE-enso-explorer/_sources/*.py` — git-versioned, public.
- **Raw sources** (KNBS/AFA PDFs, county gender sheets, CHIRPS admin extracts, staged CSVs): **D409
  OneDrive** `…/ClimateActionNetZero/1_Projects/D409_Adaptation _Atlas/2_Technical & Data/RCMRD/ENSO
  explorer/` — private, **not versioned**. Run raw-reading scripts with
  `/Users/pstewarda/miniforge3/bin/python3` (has pandas/pyarrow/pdfplumber/fitz).
- CGIAR Climate Data Hub / S3: **not yet** (no submission).
- **Provenance projection**: `provenance.json` — generated, never hand-edited. See below.

## Provenance — one generated projection, no third copy

The notebook's provenance drawer and the Section 6 master catalogue both render from
`provenance.json`, built by [`_sources/provenance_build.py`](./_sources/provenance_build.py) out of the
two upstream metadata stores in `hazards_prototype`:

| Store | Owns |
|---|---|
| `metadata/cdh/*.yaml` (CDH v0.3.0) | licence, attribution, citation, caveats (`note`), not-recommended uses, coverage, assets, processing, dimensions/variables |
| `metadata/catalogue/*.json` (issue #29) | host location, transfer strategy, stage wiring, status, `gaps[]` |

Rules (contract: `hazards_prototype/HANDOVER_2026-09-18_provenance-drawer-and-metadata-gaps.md` §1):

- **Never hand-write a licence, citation, attribution string or caveat into `notebook_v3.qmd`,
  `provenance_keymap.json` or `provenance.json`.** Those three would be a third copy and will drift.
  Fix the CDH record upstream and rebuild.
- `_sources/provenance_keymap.json` carries **ids and UI routing only** — notebook handle, aliases,
  category, which CDH/catalogue record it maps to, which parquets it backs.
- `note` is rendered **verbatim**, in full, never collapsed. That is where "255 = not observed, NOT
  dry", the SAR gaps, the GFM-vs-CHIRPS NDJ/DJF label mismatch and the KNBS 345-vs-290 admin trap live.
- Two orthogonal axes are both rendered: `state` (`authored` / `draft` / `invalid` / `catalogue-only` /
  `undocumented`) and `hosting` (`atlas` / `federated` / `unknown`). A dataset with no record renders
  **"provenance not documented"**, never a blank.

Rebuild (state is probed against the real CDH validator when a checkout is available):

```sh
git clone --depth 1 --branch v0.3.0 \
  https://github.com/CGIAR-Climate-Data-Hub/cdh-metadata-standard.git /tmp/cdh-std && (cd /tmp/cdh-std && npm ci)
uv run --with pyyaml python data/KE-enso-explorer/_sources/provenance_build.py
npm exec --yes --package=jsdom -- node data/KE-enso-explorer/_sources/provenance_drawer_test.js
```

Without the checkout the build still runs, but every entry records `state_basis: "version-probe"` —
a soft check that must not be reported as a strict one.

Current coverage (2026-09-18): **14 authored, 2 catalogue-only, 6 undocumented** of 22 entries. The 8
non-authored datasets are tracked in
`playbook/handovers/KE-enso-explorer/dispatches/2026-09-18_request-cdh-draft-records.md`.

## Reproducibility legend
- **git-full** — the script fetches the source and builds the parquet with no external inputs; anyone
  can reproduce from the repo alone.
- **git-transform** — the transform/extract script is in the repo, but it reads a **raw file held on
  D409 OneDrive** (acquisition of the raw file is not scripted in-repo).
- **D409-only** — neither acquisition nor transform is in this repo; the parquet was produced by the
  D409 OneDrive pipeline and staged here. Biggest repeatability gap.

---

## A. Novel extractions / derivations (built by this effort)

### 1. KNBS National Agriculture Production Report (NAPR)
- **Source:** KNBS, National Agriculture Production Report — 2023-24 + 2024-25 editions (county annexes).
- **URL:** <https://www.knbs.or.ke/> (Agriculture Production Report series). Raw PDFs on D409 OneDrive.
- **Acquire → build:** download the NAPR PDF(s) → `_sources/napr_build.py <NAPR2024.pdf> <NAPR2025.pdf>`
  (engine `napr_extract.py`; livestock/products via `napr_build_livestock.py` / `napr_build_products.py`).
  Reusable skill: `.claude/skills/extract-knbs-napr`.
- **Reproducibility:** git-transform (needs the raw PDFs from OneDrive).
- **Licence:** KNBS official statistics — public; cite KNBS.
- **Files:** `knbs_napr_county_production.parquet` (+`.meta.json`, stale: says 12 crops, actual 31),
  `knbs_napr_livestock.parquet` (+`.meta.json`), `knbs_napr_livestock_products.parquet`,
  `knbs_production_national.parquet` (+`.meta.json`). Provenance: `_sources/napr_audit_ledger.csv`,
  `_sources/napr_validation_report.csv`, `napr_sources.json`.

### 2. KNBS County Gender Data Sheets (GESI)
- **Source:** KNBS / State Dept for Gender, County Gender Data Sheets (2025) — 47 per-county PDFs.
- **URL:** `https://www.knbs.or.ke/wp-content/uploads/2026/0{4,5}/NN-County-…pdf` (download list
  `_urls.txt` + `download_datasheets.sh` on D409 OneDrive).
- **Acquire → build:** download the 47 PDFs → `_sources/gesi_extract.py --all "<sheets dir>"`.
  Reusable skill: `.claude/skills/extract-knbs-gender-sheets`.
- **Reproducibility:** git-transform (raw PDFs on OneDrive; download script on OneDrive).
- **Licence:** KNBS official statistics — public; cite KNBS.
- **Files:** `gesi_v2.parquet` (served, 35 series/24 codes) · `gesi.parquet` (superseded original). **No
  `.meta.json` yet.**

### 3. AFA (Agriculture & Food Authority, Kenya) — rice
- **Source:** AFA county crop returns. Only Rice folded in (KNBS omits it; all other AFA crops verified
  identical to the NAPR).
- **URL:** <https://www.afa.go.ke/> (raw extract `afa_production.parquet` staged from D409 OneDrive).
- **Acquire → build:** `_sources/afa_rice_build.py` (reads `afa_production.parquet` → `afa_rice.parquet`).
- **Reproducibility:** git-transform (needs `afa_production.parquet`, which is D409-sourced).
- **Licence:** AFA (public).
- **Files:** `afa_rice.parquet` (served) · `afa_production.parquet` (raw). **No `.meta.json` yet.**

### 4. ENSO / IOD / Western-V ocean-driver indices
- **Source:** NOAA CPC (Niño 3.4, RONI, SOI, ENSO-state probabilities); NOAA PSL (DMI/IOD, HadISST);
  Western-V (WNP/WEP) derived.
- **URLs (in the scripts, keyless):** RONI `https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt` ·
  SOI `https://www.cpc.ncep.noaa.gov/data/indices/soi` · DMI
  `https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data` · ENSO probs
  `https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/`.
- **Acquire → build:** `_sources/enso_drivers_build.py` and `_sources/enso_state_prob_build.py` —
  **self-fetching** (rerun to refresh; the CPC probabilities update monthly).
- **Reproducibility:** **git-full** for `enso_*`. `driver_indices.parquet` (Niño 3.4/DMI/Western-V
  monthly) is **D409-only** (produced by the D409 pipeline, staged here).
- **Licence:** US Government public domain (Western-V derived).
- **Files:** `enso_drivers_seasonal.parquet`, `enso_drivers_monthly.parquet`,
  `enso_state_probabilities.parquet`, `driver_indices.parquet`. **No `.meta.json` yet.**

### 5. ENSO seasonal outlook (derived analogue)
- **Source:** derived — CHIRPS county rainfall (§6) + the driver indices (§4).
- **Acquire → build:** `_sources/enso_outlook_build.py` (reads `chirps_county.parquet` +
  `enso_drivers_seasonal.parquet` → tercile analogue base).
- **Reproducibility:** git-full given §4 + §6 parquets are present.
- **Licence:** derived (CHIRPS CC-BY + NOAA public domain).
- **Files:** `enso_outlook_base.parquet`. **No `.meta.json` yet.**

---

## B. Third-party data harmonized to Kenya's 47 counties

### 6. CHIRPS county rainfall / climate — UCSB Climate Hazards Center (via Atlas climate hub)
- **Source:** CHIRPS v3 precip + CHIRTS-ERA5 temp + SPEI, admin1 zonal.
- **URLs:** Atlas hub S3 `https://digital-atlas.s3.amazonaws.com/domain=climate/type=observational/
  source=chirps-chirts-era5/region=africa/processing=admin-monthly|admin-periods/variable=adm1_obs.parquet`;
  raw rasters `https://data.chc.ucsb.edu/products/CHIRPS/v3.0/`.
- **Reproducibility:** D409-only (zonal extraction ran in the D409 pipeline; staged here).
- **Licence:** CC-BY (CHC).
- **Files:** `chirps_county.parquet` (seasonal, PTOT+temp+SPEI, 1980–2026) ·
  `chirps_county_monthly.parquet` (monthly PTOT, 1981–2026). **No `.meta.json` yet.**

### 7. FAOSTAT national production — FAO
- **Source/URL:** <https://www.fao.org/faostat/en/#data/QCL>. **Reproducibility:** D409-only.
- **Licence:** CC-BY (FAO). **Files:** `faostat.parquet`, `faostat_detrended.parquet`.

### 8. FEWS NET — food security · prices · trade (one source, 3 series)
- **Source/URLs:** IPC <https://fews.net/>; FDW retail prices <https://fdw.fews.net/>; cross-border trade
  <https://fews.net/>. **Reproducibility:** `xbt_trade` has `_sources/parse_xbt.py` (git-transform);
  `ipc_county` + `market_prices` are D409-only.
- **Licence:** FEWS NET — reading and display unencumbered. **Redistribution caveat:** FEWS NET states
  that third-party series held in the warehouse may not be redistributed without the originating
  provider's consent, and market prices are usually collected by national agencies. Display is fine;
  **identify the originating agency for a given series before republishing it.**
- **Terms of trade is ours, not FEWS'.** No agency publishes it. The notebook derives it client-side
  (`notebook_v3.qmd` `totRows`) as median goat price (KES/head) ÷ median maize-grain price (KES/kg) per
  county-month. Being a ratio it is ambiguous alone — a fall can mean cheaper livestock **or** dearer
  grain, which imply opposite responses — so it must be read against both price legs.
- **NDMA is not a source here.** No NDMA bulletin is ingested anywhere in this notebook. Earlier
  "FEWS NET / NDMA" provenance strings were unsupported and were removed (2026-09-18). NDMA still
  appears as an *institution* (KMSA bulletin co-authorship, the Table 4.3 advisory directory) — that is
  a statement about those bodies, not about our data.
- **Files:** `ipc_county.parquet` · `market_prices.parquet` · `xbt_trade.parquet` (+`.meta.json`).

### 9. ACLED — conflict
- **Source/URL:** <https://acleddata.com/> (API, registration + attribution required).
- **Reproducibility:** D409-only. **Licence:** ACLED attribution licence (not fully open).
- **Files:** `acled_conflict.parquet`. **No `.meta.json` yet.**

### 10. WFP VAM — NDVI vegetation condition
- **Source/URL:** WFP VAM / HDX <https://data.humdata.org/> (MODIS-derived).
- **Reproducibility:** `_sources/parse_ndvi.py` (git-transform). **Licence:** CC-BY (WFP VAM / OCHA COD).
- **Files:** `ndvi_county.parquet` (+`.meta.json`).

### 11. ReliefWeb — humanitarian reports (UN OCHA)
- **Source/URL:** <https://reliefweb.int/> API (appname `steward-cgiar-aaa-atlas-enso-…` registered).
- **Reproducibility:** D409-only (`impacts/reliefweb_pipeline.py` on OneDrive). **Licence:** OCHA terms.
- **Files:** `reliefweb_county.parquet`. **No `.meta.json` yet.**

### 12. Exposure / value of production — MapSPAM + GLW4 (Atlas)
- **Source/URL:** MapSPAM <https://mapspam.info/>; Gridded Livestock of the World 4 (FAO). Via Atlas hub.
- **Reproducibility:** `_sources/parse_exposure.py` (git-transform). **Licence:** CC-BY.
- **Files:** `exposure_vop.parquet` (+`.meta.json`).

### 13. JRC ASAP — crop calendar
- **Source/URL:** <https://mars.jrc.ec.europa.eu/asap/>. **Reproducibility:** `_sources/parse_seasonal_calendar.py`
  (git-transform). **Licence:** JRC open data (Decision 2011/833/EU).
- **Files:** `seasonal_calendar.parquet` (+`.meta.json`).

### 14. HarvestStat Africa — county crop production by season (FDW / Kenya MoALD)
- **Source:** HarvestStat Africa v1.2 (Lee et al. 2025, Sci Data 10.1038/s41597-025-05001-z) —
  harmonized FEWS NET Data Warehouse records whose sole Kenya source is the **Ministry of
  Agriculture & Livestock Development** (same reporting chain as the NAPR). Scan + provenance
  verification: 2026-08-13.
- **URL:** <https://github.com/HarvestStat/HarvestStat-Africa> (`public/hvstat_africa_data_v1.2.csv`,
  pinned to tag `v1.2`).
- **Acquire → build:** `_sources/harveststat_build.py` — self-fetching (downloads the pinned CSV,
  filters Kenya, joins `gaul1_code` via `county_key`, gate = 47/47 counties match).
- **Reproducibility:** **git-full** (no OneDrive input).
- **Licence:** MIT (HarvestStat); underlying statistics Kenya MoALD via FEWS NET — cite both.
- **Coverage:** 39 crops × 47 counties, harvest years 1965–2024. Seasons: Annual 1974–2020;
  **Long** (plant Mar → harvest Aug) & **Short** (plant Oct → harvest Mar **next year**; lag explicit
  via `planting_year`/`harvest_year`) 1991–2001 + 2015/16–2024. **Seasonal hole 2002–2014** (Annual
  only). Pre-2013 rows are HarvestStat's district→county remap (1989 districts ≈ 1:1 with counties).
- **Caveat:** maize cross-check vs NAPR 2019–24 = r 0.94, median ratio 0.92–1.04/yr, but per-county
  vintages differ up to ~2× — never present HarvestStat and NAPR values as interchangeable.
  HarvestStat = historical/seasonal time series; NAPR = current-level facts.
- **Files:** `harveststat_county_production.parquet` (+`.meta.json`). Not yet served by the notebook —
  registered for the production×climate design (ISSUES KE-18 / V2-15 / V2-27).

### (Reference) county ↔ GAUL24 lookup
`county_key.parquet` — join key (FAO GAUL 2024); not a standalone dataset.

---

## State summary
- **14 source-grouped datasets** (5 novel + 9 harmonized) from **27 parquet files** + 1 reference lookup.
- Reproducible from git alone: **git-full** = the `enso_*` driver/outlook set (§4 self-fetch, §5 derived)
  + `harveststat_county_production` (§14 self-fetch).
  **git-transform** = NAPR, GESI, AFA-rice, NDVI, XBT, exposure, ASAP (script in repo, raw on OneDrive).
  **D409-only** = CHIRPS, FAOSTAT, IPC, market prices, ACLED, ReliefWeb, driver_indices.
- `.meta.json` present for **all 26 parquet files** (written/refreshed 2026-08-07 by
  `_sources/meta_build.py`; re-run after any dataset change). Each records source, URL, citation,
  licence, method, coverage, columns, used_by.
- Publicly reachable as GitHub blobs: all. Submitted to the CGIAR Climate Data Hub: **0**.

## To make fully repeatable + Hub-ready (open actions)
1. ~~Add `.meta.json` for every dataset~~ **DONE (2026-08-07)** — all 26 via `_sources/meta_build.py`.
2. Bring the **D409-only** acquisition steps into `_sources/` as scripts (or copy the D409 pipeline
   scripts here) so CHIRPS/FAOSTAT/IPC/prices/ACLED/ReliefWeb/driver_indices are git-reproducible.
3. Move raw sources to a versioned/citable store (or record exact source URLs + retrieval dates per file).
4. Submit the novel datasets to the CGIAR Climate Data Hub against its metadata standard.
