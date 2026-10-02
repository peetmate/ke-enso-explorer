# ken_adm{1,2}_iebc_simple.topojson — provenance

**Two files, same recipe:** `ken_adm1_iebc_simple.topojson` (47 counties, 57 KB) +
`ken_adm2_iebc_simple.topojson` (290 sub-counties, 179 KB). Both are the official Kenya boundaries
used across BOTH notebooks (map prototype + main) in place of GAUL — GAUL carries the disputed **Ilemi
Triangle** (a 48th GAUL "county") and has no p-codes; IEBC is the Kenya-government-authoritative set.

**`gaul1_code` injected** into every feature by matching `admin1_name` → the GAUL a1 topojson's
gaul1_code (47/47 counties matched; only GAUL-only unit = Ilemi Triangle, correctly dropped). This lets
existing `gaul1_code`-keyed data joins work unchanged against the IEBC geometry. Props on each feature:
`admin1_name, admin1_pcode, gaul1_code` (+ `admin2_name, admin2_pcode` on adm2), `area_sqkm`.



Browser-ready simplified IEBC sub-county (admin-2) boundaries for the KE-39 flood/exposure
admin-2 selection + intersect UI.

- **Source:** cglabs-published authoritative IEBC COD-AB (HDX, source=IEBC, CC-BY-IGO):
  `digital-atlas.s3.amazonaws.com/domain=boundaries/type=admin/source=iebc-codab/region=kenya/processing=analysis-ready/level=adm2/ken_adm2.geojson`
  (raw ~11 MB, 290 sub-counties, official `adm1_pcode`/`adm2_pcode`).
- **Why simplified:** the raw GeoJSON is ~11 MB — too heavy to load client-side. This matches the
  Atlas shared-vector convention (`data/shared/atlas_gaul24_a2_africa_simple-lowres.topojson` = 3.2 MB
  for ALL of Africa, quantized topojson).
- **Recipe (mapshaper 0.7.55):**
  ```
  mapshaper ken_adm2.geojson \
    -filter-fields adm1_name,adm1_pcode,adm2_name,adm2_pcode,area_sqkm \
    -rename-fields admin1_name=adm1_name,admin1_pcode=adm1_pcode,admin2_name=adm2_name,admin2_pcode=adm2_pcode \
    -simplify 8% keep-shapes -clean \
    -o format=topojson quantization=100000 ken_adm2_iebc_simple.topojson
  ```
- **Output:** 179 KB (≈58 KB gzipped); topojson object `ken_adm2`; 290 features, 0 null geometries,
  47 distinct counties; props: `admin1_name, admin1_pcode, admin2_name, admin2_pcode, area_sqkm`.
- **Use in notebook:** `FileAttachment("/data/KE-enso-explorer/ken_adm2_iebc_simple.topojson").json()`
  then `topojson-client` `feature()` / `merge()` — same pattern as the existing `kenA2` (GAUL a2).
  **Prefer this over GAUL a2 when official p-codes matter** (GAUL a2 has Kenya's 291 sub-county
  geometries but NO p-codes + the disputed Ilemi unit). See
  [[reference_kenya-gaul-admin2-districts]] / dispatch `2026-08-24_cglabs-reply-ke39-exposure-status.md`.
