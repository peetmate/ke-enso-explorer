#!/usr/bin/env python3
"""Write/refresh per-dataset .meta.json records for the KE-ENSO parquets.

One record per dataset: title, source, url, citation, licence, method, coverage,
columns (pulled live from the parquet so names are exact), used_by. Facts are
hand-authored from DATA.md; column NAMES are read from the file. Re-run after a
dataset changes. See DATA.md for the source/storage manifest.

Usage:  python3.12 meta_build.py
"""
import json, pyarrow.parquet as pq

OUT = "data/KE-enso-explorer"

# hand-authored facts per dataset (accurate; see DATA.md). Columns added live.
D = {
 "knbs_napr_county_production": dict(  # refresh stale record (was "12 crops")
   title="KNBS county crop production (Area + Production), Kenya",
   source="KNBS National Agriculture Production Report — 2023-24 edition (2019-2023) + 2024-25 edition (2024, provisional)",
   url="https://www.knbs.or.ke/ (Agriculture Production Report series)",
   citation="KNBS. National Agriculture Production Report. Nairobi, Kenya.",
   license="KNBS official statistics — public; cite KNBS.",
   fetched_on="2026-07-22",
   method="Deterministic dual-engine extraction (_sources/napr_extract.py + napr_build.py): pymupdf-authoritative + pdfplumber cross-check, coordinate column-binning, orientation auto-detect, wrapped-name merge. A crop-county-year is served only if the county sum reconciles to the annex's printed national Total (additivity) and, where the 2nd engine reads the page, the two agree cell-by-cell. Cross-edition rebase to the latest edition. No number read/typed by a model.",
   coverage="31 crops, 2019-2024 (2024 provisional from the 2025 edition). Cross-edition overlap rebased to the 2025 edition; edition diffs in _sources/edition_diffs_2024ed_vs_2025ed.csv.",
   used_by="notebook §1.1 'What does my county produce?' (Crops view)"),
 "knbs_napr_livestock": dict(
   title="KNBS county livestock population, Kenya",
   source="KNBS National Agriculture Production Report (2023-24 + 2024-25 editions), livestock annexes",
   url="https://www.knbs.or.ke/",
   citation="KNBS. National Agriculture Production Report. Nairobi, Kenya.",
   license="KNBS official statistics — public; cite KNBS.",
   fetched_on="2026-07-20",
   method="Deterministic extraction (_sources/napr_build_livestock.py) via the napr_extract engine; dual-engine + cross-year plausibility (±50%) gate. No number typed by a model.",
   coverage="13 species, head, 2021-2023.",
   used_by="notebook §1.1 produce (Livestock view)"),
 "knbs_production_national": dict(
   title="KNBS national agricultural production, Kenya",
   source="KNBS National Agriculture Production Report (national totals)",
   url="https://www.knbs.or.ke/",
   citation="KNBS. National Agriculture Production Report. Nairobi, Kenya.",
   license="KNBS official statistics — public; cite KNBS.",
   fetched_on="2026-07-17",
   method="Deterministic extraction of the report's printed national totals (napr engine).",
   coverage="National production series.",
   used_by="notebook — national context / additivity reference"),
 "gesi_v2": dict(
   title="Gender & equity indicators (GESI), Kenya counties",
   source="KNBS County Gender Data Sheets (2025) — 47 per-county PDFs (State Dept for Gender + KNBS + UN Women 'Women Count')",
   url="https://www.knbs.or.ke/wp-content/uploads/2026/0{4,5}/NN-County-...pdf",
   citation="KNBS / State Department for Gender. County Gender Data Sheets, 2025. Nairobi, Kenya.",
   license="UNRESOLVED — do not assert. The sheets carry six parties (County Government, Council of Governors, State Dept for Gender & Affirmative Action, KNBS, SDGs Kenya Forum, UN Women 'Women Count'), no copyright notice, no ISBN. Absence of a notice is NOT a licence grant. The KNBS Open License Agreement is scoped to the Open Data Platform (kenya.opendataforafrica.org) and these are PDFs on knbs.or.ke, so it almost certainly does not reach them — same gap as Census Volume XVI. Not published to S3; settle with UN Women before any redistribution.",
   fetched_on="2026-07-24",
   method="Code-keyed deterministic extraction (_sources/gesi_extract.py): keys on the sheet's stable indicator code (not label text). Validation gate = the Kenya national value is identical on all 47 sheets per indicator; a series is served only if >=40/47 counties match the modal Kenya value. No number typed by a model.",
   coverage="35 indicator series across 24 codes, county level (adm1). Coverage is NOT uniform: the gate serves a series at >=40/47, so only 10 of 35 series reach all 47 counties (10 at 46, 3 at 45, 5 at 44, 3 at 43, 2 at 42, 2 at 40; worst is B6 households-with-elderly at 40/47). Per-county rows run 22-35. A missing county-series is a gate/parse drop, NEVER an observed zero. D7 is sex-asymmetric (Male 47, Female 46) - check both before any sex ratio. Chart-style indicators (ANC-visit/vaccination charts, internet-usage) dropped by the gate. Reference year is NOT retained: clean_label() strips trailing years, and the sheets mix vintages (KDHS 2022, 2019 census-derived), so the table must not be read as uniformly 2022.",
   used_by="notebook §2.1 GESI 47-county distribution"),
 "ndma_bulletin_index": dict(
   title="NDMA drought early warning bulletin index, Kenya",
   source="National Drought Management Authority (NDMA) KnowledgeWeb document library — National (ID=7) + County (ID=11) Drought Early Warning Bulletin categories",
   url="https://knowledgeweb.ndma.go.ke/Public/Resources/Default.aspx?ID={7,11}",
   citation="National Drought Management Authority (NDMA). Drought Early Warning Bulletins. Nairobi, Kenya.",
   license="UNRESOLVED — do not assert. NDMA KnowledgeWeb publishes no terms page, no robots.txt and no copyright notice; absence of a notice is NOT a licence grant. This dataset holds METADATA ABOUT PUBLIC DOCUMENTS (title, uuid, category, upload date, plus a derived county and reference period) together with deep links back to NDMA's own pages — citation and federation, the weakest-risk end. It is NOT a settled basis for republishing values extracted from the PDF bodies; settle that before any extraction phase. No PDF bytes are redistributed.",
   fetched_on="2026-09-27",
   method="Deterministic harvest of NDMA's own grid (_sources/ndma_index_build.py). Paging is a DevExpress ASPxGridView callback (__CALLBACKID=ctl00$ContentPlaceHolder1$docGrid, __CALLBACKPARAM=c0:KV|..;GB|..;12|PAGERONCLICK3|PN<n>;) carrying a grid-state hidden field that is generated client-side and never appears in the served HTML — without it the server returns an empty grid with HTTP 200. Completeness gate: every sweep enumerates exactly the row count the SITE reports, checked per page against the server's own 'Page n of N (M items)' echo; distinct documents plus NDMA's repeated listings reconcile to that row count; and a SECOND sweep under a different column sort surfaces zero new documents, which is what rules out offset paging silently dropping rows. NO PDF is downloaded or parsed and NO indicator value is extracted. County and reference period are parsed from the grid title text; unresolved values are NULL, never guessed, and every served county is asserted against county_key.parquet.",
   coverage="3,513 documents: 3,406 county bulletins (2012-08 to 2026-08) across 23 ASAL counties, and 107 national bulletins (2016-10 to 2026-08). THREE TRAPS. (1) `uploaded_date` is the UPLOAD date, NOT the bulletin's reference period — the back catalogue was bulk-uploaded in Dec 2021 (1,537 of 3,513 rows carry a 2021 upload date, including bulletins referencing 2012-2018), so a time series built on it is wrong by up to nine years; use `ref_period`, parsed from the title, and check `ref_basis`. (2) NDMA's county category lists 3,410 ROWS but only 3,406 DISTINCT documents — four documents are listed twice at different offsets with the same grid key; the index carries one row per document and the duplicate uuids are recorded in _sources/ndma_index_validation_report.csv. (3) NDMA covers ASAL counties ONLY — 23 of 47. A missing county is structural and NEVER a zero. `ref_basis` flags derivation quality: 3,499 title-month-year, 5 month-and-year-apart, 3 year-only, 6 unparsed (NULL period). `doc_year_grid` is sparse and must not be used as the period.",
   used_by="index only — not yet wired to the notebook; the join key for a later bulletin-extraction phase"),
 "afa_rice": dict(
   title="AFA county rice production & area, Kenya",
   source="Agriculture & Food Authority (AFA), Kenya — county crop returns (Rice only)",
   url="https://www.afa.go.ke/",
   citation="Agriculture & Food Authority (AFA), Kenya. County crop production returns.",
   license="AFA — public.",
   fetched_on="2026-07-24",
   method="Deterministic build (_sources/afa_rice_build.py). Only Rice is folded in — the one crop the KNBS NAPR county tables omit; every other AFA crop is identical to the NAPR (233/234 maize county-years matched) and is not double-counted.",
   coverage="Rice, 17 counties, 2020-2024, area (ha) + production (t).",
   used_by="notebook §1.1 produce (folded into the KNBS crop set)"),
 "enso_drivers_seasonal": dict(
   title="ENSO/IOD driver indices, seasonal",
   source="NOAA CPC (RONI, SOI) + NOAA PSL (DMI/IOD, HadISST)",
   url="https://www.cpc.ncep.noaa.gov/data/indices/ ; https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data",
   citation="NOAA Climate Prediction Center; NOAA Physical Sciences Laboratory (HadISST, Met Office Hadley Centre).",
   license="US Government public domain.",
   fetched_on="2026-07-23",
   method="Self-fetching build (_sources/enso_drivers_build.py): parses the source ASCII; SOI/DMI seasonalised to 3-month overlapping seasons; RONI native seasonal. Spot-checked vs source. Rerun to refresh.",
   coverage="RONI 1950-2026, SOI 1951-2026, DMI 1870-2025; 12 seasons.",
   used_by="notebook §7 outlook analogue matching + driver context"),
 "enso_drivers_monthly": dict(
   title="ENSO/IOD driver indices, monthly",
   source="NOAA CPC (SOI) + NOAA PSL (DMI/IOD, HadISST)",
   url="https://www.cpc.ncep.noaa.gov/data/indices/soi ; https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/dmi.had.long.data",
   citation="NOAA Climate Prediction Center; NOAA Physical Sciences Laboratory.",
   license="US Government public domain.",
   fetched_on="2026-07-23",
   method="Self-fetching build (_sources/enso_drivers_build.py). Rerun to refresh.",
   coverage="SOI + DMI monthly, 1870/1951-2026.",
   used_by="notebook §7 driver time-series"),
 "enso_state_probabilities": dict(
   title="CPC ENSO-state probability forecast",
   source="NOAA CPC official RONI-based probabilistic ENSO forecast",
   url="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/probabilities/",
   citation="NOAA Climate Prediction Center. Official probabilistic ENSO forecast.",
   license="US Government public domain.",
   fetched_on="2026-07-23",
   method="Self-fetching build (_sources/enso_state_prob_build.py): parses the official HTML table; each row gated to sum ~100%. Refreshes monthly — rerun to update.",
   coverage="El Nino / Neutral / La Nina probabilities for 9 overlapping 3-month seasons; issue month in the 'issued' column.",
   used_by="notebook §7.2 outlook forecast phase (D14-allowed ENSO-state forecast)"),
 "enso_outlook_base": dict(
   title="ENSO seasonal-outlook analogue base (MAM/OND), Kenya counties",
   source="Derived — CHIRPS county rainfall + ENSO/IOD driver indices",
   url="(derived; see chirps_county + enso_drivers_seasonal)",
   citation="Derived product; underlying CHIRPS (UCSB CHC) + NOAA CPC/PSL indices.",
   license="Derived — CHIRPS CC-BY + NOAA public domain.",
   fetched_on="2026-07-23",
   method="_sources/enso_outlook_build.py: per target season (MAM<-DJF, OND<-JAS predictor) + county-year, computes seasonal rainfall vs the 1991-2020 normal, Dry/Near/Wet tercile, and predictor + concurrent driver state. Validated: OND El Nino years ~all Wet, La Nina ~Dry.",
   coverage="MAM + OND, 47 counties + Ilemi Triangle, 1981-2025.",
   used_by="notebook §7.2 analogue likely-outcome map + card"),
 "chirps_county_monthly": dict(
   title="CHIRPS monthly county rainfall, Kenya",
   source="UCSB Climate Hazards Center — CHIRPS v3 (admin1 zonal, via the Atlas climate hub)",
   url="https://data.chc.ucsb.edu/products/CHIRPS/v3.0/ ; Atlas hub digital-atlas S3 admin-monthly",
   citation="Funk et al., CHIRPS v3, UCSB Climate Hazards Center.",
   license="CC-BY (UCSB Climate Hazards Center).",
   fetched_on="2026-07-27",
   method="Pre-extracted admin1 zonal mean from the Atlas climate hub (no raster work); PTOT filtered + renamed to the notebook schema.",
   coverage="Monthly precipitation (mm), 47 counties, 1981-2026.",
   used_by="notebook §3.1 monthly rainfall climatology"),
 "faostat": dict(
   title="FAOSTAT national crop production, Kenya",
   source="FAO FAOSTAT (Crops and livestock products, QCL)",
   url="https://www.fao.org/faostat/en/#data/QCL",
   citation="FAO. FAOSTAT. Rome.",
   license="CC-BY (FAO).",
   fetched_on="2026-07-10",
   method="Machine-readable FAOSTAT bulk download (no transcription); staged via the D409 pipeline.",
   coverage="National production, 1961-2024.",
   used_by="notebook §4 (national production × driver)"),
 "faostat_detrended": dict(
   title="FAOSTAT national production, detrended anomalies",
   source="FAO FAOSTAT (QCL), detrended",
   url="https://www.fao.org/faostat/en/#data/QCL",
   citation="FAO. FAOSTAT. Rome.",
   license="CC-BY (FAO).",
   fetched_on="2026-07-10",
   method="FAOSTAT production detrended (trend removed) to compare stationary anomalies against the driver indices.",
   coverage="1961-2024; trend, anomaly, pct_anom, trend_slope columns.",
   used_by="notebook §4 detrended production × driver"),
 "ipc_county": dict(
   title="IPC food-security phase, Kenya counties",
   source="IPC via FEWS NET",
   url="https://fews.net/",
   citation="FEWS NET / IPC.",
   license="FEWS NET — public.",
   fetched_on="2026-07-10",
   method="Machine-readable FEWS/IPC source; staged via the D409 pipeline (D409-only acquisition).",
   coverage="County IPC phase (max/mean), multiple reporting dates.",
   used_by="notebook §5.1 food-security phase"),
 "market_prices": dict(
   title="FEWS NET retail market prices, Kenya",
   source="FEWS NET Data Warehouse (FDW), marketpricefacts",
   url="https://fdw.fews.net/",
   citation="FEWS NET Data Warehouse (FDW).",
   license="FEWS NET — reading and display unencumbered. REDISTRIBUTION CAVEAT: FEWS NET states that third-party series held in the warehouse may not be redistributed without the originating provider's consent, and market prices are usually collected by national agencies. Display is fine; identify the originating agency for a given series before republishing it.",
   fetched_on="2026-07-15",
   method="Machine-readable FEWS FDW retail prices; staged via the D409 pipeline. Terms of trade is NOT in this file and is NOT sourced — the notebook derives it client-side as median goat price (KES/head) / median maize-grain price (KES/kg) per county-month. It is a ratio: a fall can mean cheaper livestock or dearer grain, which carry opposite implications, so it must be read against both price legs.",
   coverage="County x market x product monthly prices (KES), retail + wholesale, 42 counties, 2000-2026.",
   used_by="notebook §5.3 market prices + derived terms of trade"),
 "acled_conflict": dict(
   title="ACLED conflict events, Kenya counties",
   source="ACLED — Armed Conflict Location & Event Data",
   url="https://acleddata.com/",
   citation="Raleigh et al. ACLED. acleddata.com.",
   license="ACLED attribution licence (registration + attribution; not fully open).",
   fetched_on="2026-07-10",
   method="ACLED API (registration); staged via the D409 pipeline (D409-only acquisition).",
   coverage="County-week events + fatalities by event/disorder type.",
   used_by="notebook §5.2 conflict (climate-conflict signal is exploratory)"),
 "reliefweb_county": dict(
   title="ReliefWeb humanitarian reports, Kenya counties",
   source="UN OCHA ReliefWeb",
   url="https://reliefweb.int/",
   citation="UN OCHA ReliefWeb.",
   license="UN OCHA ReliefWeb terms of use.",
   fetched_on="2026-07-15",
   method="ReliefWeb API (registered appname); pipeline impacts/reliefweb_pipeline.py on D409 OneDrive.",
   coverage="County-tagged situation reports (id, date, title, disaster type, url).",
   used_by="notebook §5.4 humanitarian reports"),
 "chirps_county": dict(
   title="CHIRPS county rainfall & climate (seasonal), Kenya",
   source="UCSB Climate Hazards Center — CHIRPS v3 precip + CHIRTS-ERA5 temp + SPEI (admin1 zonal, via the Atlas climate hub)",
   url="https://data.chc.ucsb.edu/products/CHIRPS/v3.0/ ; Atlas hub digital-atlas S3 admin-periods",
   citation="Funk et al., CHIRPS v3 + CHIRTS-ERA5, UCSB Climate Hazards Center.",
   license="CC-BY (UCSB Climate Hazards Center).",
   fetched_on="2026-07-10",
   method="Pre-extracted admin1 zonal from the Atlas climate hub (no raster work); staged via the D409 pipeline.",
   coverage="County x year x period (seasons + annual) x variable: PTOT (mm), TAVG/TMAX/TMIN (C), SPEI-01/03/06/12/24. 1980-2026.",
   used_by="notebook §3 rainfall by season + §7 outlook base"),
 "knbs_napr_livestock_products": dict(
   title="KNBS county livestock products (quantity + value), Kenya",
   source="KNBS National Agriculture Production Report, livestock-products annexes",
   url="https://www.knbs.or.ke/",
   citation="KNBS. National Agriculture Production Report. Nairobi, Kenya.",
   license="KNBS official statistics — public; cite KNBS.",
   fetched_on="2026-07-20",
   method="Deterministic extraction (_sources/napr_build_products.py); gated on the value = quantity x unit-price identity + cross-year plausibility. No number typed by a model.",
   coverage="11 products, quantity + value, 2021-2022.",
   used_by="notebook §1.1 produce (Products view)"),
 "county_key": dict(
   title="County to GAUL24 admin1 lookup, Kenya",
   source="FAO GAUL 2024 administrative boundaries (Atlas shared)",
   url="/data/shared/atlas_gaul24_a1_africa_simple-vlowres.topojson",
   citation="FAO GAUL 2024.",
   license="FAO GAUL (licence unstated in-repo).",
   fetched_on="2026-07-10",
   method="Canonical county name to gaul1_code join key. Reference table, not a standalone dataset.",
   coverage="47 counties + gaul1_code.",
   used_by="notebook — join key for every county dataset"),
 "afa_production": dict(
   title="AFA raw crop production extract, Kenya (raw — superseded except Rice)",
   source="Agriculture & Food Authority (AFA), Kenya — county crop returns",
   url="https://www.afa.go.ke/",
   citation="Agriculture & Food Authority (AFA), Kenya.",
   license="AFA — public.",
   fetched_on="2026-07-10",
   method="Raw AFA extract. STATUS: retained for provenance only. All crops except Rice are identical to the KNBS NAPR (verified) and are NOT served; only Rice is folded in via afa_rice.parquet.",
   coverage="15 crops, area/production/value, 2019-2024 (+ some crop-year splits). Only Rice served.",
   used_by="not served directly; see afa_rice"),
 "gesi": dict(
   title="GESI indicators, Kenya counties (SUPERSEDED original extraction)",
   source="KNBS County Gender Data Sheets (2025)",
   url="https://www.knbs.or.ke/",
   citation="KNBS / State Department for Gender. County Gender Data Sheets, 2025.",
   license="KNBS official statistics — public; cite KNBS.",
   fetched_on="2026-07-10",
   method="STATUS: SUPERSEDED by gesi_v2. Original label-keyed extraction fragmented one indicator into many near-duplicate labels (142 variants, only 9 reaching all 47 counties). Replaced by the code-keyed, Kenya-value-consistency-gated gesi_v2. Retained for provenance only.",
   coverage="Not served — see gesi_v2.",
   used_by="not served; superseded by gesi_v2"),
 "harveststat_county_production": dict(
   title="HarvestStat Africa — Kenya county crop production by season (Long/Short/Annual)",
   source="HarvestStat Africa v1.2 (Lee et al. 2025) — FEWS NET Data Warehouse records originating from the Ministry of Agriculture & Livestock Development, Kenya",
   url="https://github.com/HarvestStat/HarvestStat-Africa (public/hvstat_africa_data_v1.2.csv, tag v1.2)",
   citation="Lee, D., et al. HarvestStat Africa — Harmonized Subnational Crop Statistics for Sub-Saharan Africa. Sci Data (2025). doi:10.1038/s41597-025-05001-z",
   license="MIT (HarvestStat); underlying statistics Kenya MoALD via FEWS NET — public, cite both.",
   fetched_on="2026-08-13",
   method="Deterministic subset (_sources/harveststat_build.py): fetch the pinned v1.2 CSV from GitHub, filter Kenya, join gaul1_code via county_key (gate: 47/47 counties match), rename to repo conventions. No number touched. Upstream harmonization (HarvestStat): FDW boundary vintages KE1982A2(41)/KE1989A2(47)/KE2009A2(47) remapped onto KE2013A1 47 counties by production-based ratios; 1989 districts ~1:1 with counties. Cross-check vs knbs_napr_county_production maize 2019-24: r=0.94 levels, median ratio 0.92-1.04/yr, but per-county vintages differ up to ~2x — do NOT present the two as interchangeable numbers.",
   coverage="39 crops, 47 counties, harvest years 1965-2024. Seasons: Annual 1974-2020; Long (plant Mar, harvest Aug) & Short (plant Oct, harvest Mar NEXT year — lag explicit via planting_year/harvest_year) 1991-2001 + 2015/16-2024. SEASONAL HOLE 2002-2014 (Annual only). qc_flag: 0=clean (98%), 1/2=flagged by HarvestStat QC.",
   used_by="not yet served — registered for the production-vs-drivers design (ISSUES KE-18 / V2-15 / V2-27)"),
 "driver_indices": dict(
   title="Ocean-driver indices (Nino 3.4 / IOD / Western-V), monthly",
   source="NOAA (Nino 3.4), Met Office HadISST / NOAA PSL (DMI), derived Western-V (WNP/WEP)",
   url="https://www.cpc.ncep.noaa.gov/ ; https://psl.noaa.gov/",
   citation="NOAA CPC; NOAA PSL / Met Office Hadley Centre; Western-V derived (Funk et al. basis).",
   license="US Government public domain (Western-V derived).",
   fetched_on="2026-07-10",
   method="Staged via the D409 pipeline (D409-only acquisition). Nino 3.4 reproduces NOAA r=0.998; Western-V reproduces Funk's sign + post-1997 regime shift.",
   coverage="Monthly, 1950-2026: nino34_anom_noaa, dmi_hadisst, wep_std_ond, wnp_std_mam, nino34_std_ersst, dmi_ersst.",
   used_by="notebook §2/§3 ocean drivers"),
}


def main():
    n = 0
    for name, meta in D.items():
        f = f"{OUT}/{name}.parquet"
        df = pq.read_table(f).to_pandas()
        rec = {"dataset": name, **meta}
        rec["grain"] = f"{len(df)} rows"
        rec["columns"] = list(df.columns)
        if name == "ndma_bulletin_index":
            rec["fetched_on"] = str(df.harvested_at.max())[:10]
            rec["observed_coverage"] = {str(series): dict(rows=len(group),
                first_reference=group.ref_period.dropna().min(), last_reference=group.ref_period.dropna().max(),
                latest_upload=str(group.uploaded_date.max())) for series, group in df.groupby("series")}
            rec["coverage"] = (
                f"{len(df):,} distinct documents; " + "; ".join(
                    f"{series}: {v['rows']:,} rows, reference periods {v['first_reference']} to {v['last_reference']}"
                    for series, v in rec["observed_coverage"].items()) + ". "
                f"{df.loc[df.scope.eq('county'), 'county'].nunique()} resolved ASAL counties. "
                "Upload date is not reference date; missing counties or periods are not zero. "
                "Repeated source listings are reconciled in the two-order closure validation report."
            )
            meanings = {
                "doc_uuid": "NDMA document UUID and primary key", "grid_key": "Source grid row key",
                "category": "Source library category label", "category_id": "Source library category ID",
                "series": "National or county drought bulletin series", "scope": "National or county scope",
                "title_raw": "Unmodified source title", "county_raw": "County token parsed from title",
                "county": "Canonical county; null for national or unresolved titles",
                "gaul1_code": "Canonical county code joined from county_key",
                "ref_year": "Reference year parsed from title", "ref_month": "Reference month parsed from title",
                "ref_period": "Reference period parsed from title; never inferred from upload date",
                "ref_basis": "Period parsing method", "doc_year_grid": "Sparse source Document Year, not reference period",
                "uploaded_date": "Library upload date, not bulletin reference date",
                "uploaded_label": "Raw upload-date label", "detail_url": "Official document detail URL",
                "pdf_url": "Official document download URL; PDF bodies not redistributed",
                "page_index": "Source grid page offset", "row_index": "Source row offset on page",
                "harvested_at": "UTC harvest timestamp",
            }
            rec["fields"] = {c:dict(type=str(df[c].dtype), description=meanings[c],
                unit="date/time" if c in ("uploaded_date", "ref_period", "harvested_at") else "source label/code",
                null_semantics="Absent, unresolved or inapplicable; never zero-imputed",
                lineage="NDMA KnowledgeWeb grid; ndma_index_build.py; county_key.parquet for county codes") for c in df.columns}
            rec["primary_key"] = ["doc_uuid"]
            rec["validation_report"] = "_sources/ndma_index_validation_report.csv"
        with open(f"{OUT}/{name}.meta.json", "w") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=2)
        n += 1
        print(f"wrote {name}.meta.json ({len(df)} rows, {len(df.columns)} cols)")
    print(f"\n{n} metadata records written/refreshed.")


if __name__ == "__main__":
    main()
