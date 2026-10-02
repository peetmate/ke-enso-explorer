/* provenance_drawer_test.js — smoke test for the provenance drawer + Section 6 catalogue.
 *
 * Runs helpers/provenanceDrawer.js against the REAL markup spliced out of notebook_v3.qmd
 * and the REAL generated projection, so it fails when either drifts. It checks the four
 * things the contract makes non-negotiable
 * (HANDOVER_2026-09-18_provenance-drawer-and-metadata-gaps.md §1):
 *   - every openMethodDrawer()/jumpToDataset() call site in the qmd resolves to a card;
 *   - the legally-required attribution strings appear verbatim;
 *   - caveats and not_recommended_for are rendered and never inside a <details>;
 *   - a thin record looks thin, a missing one says "provenance not documented", and an
 *     unknown key never falls back to some other dataset's record.
 *
 * Run (from the repo root):
 *   npm exec --yes --package=jsdom -- node data/KE-enso-explorer/_sources/provenance_drawer_test.js
 * Rebuild the projection first if records changed:
 *   uv run --with pyyaml python data/KE-enso-explorer/_sources/provenance_build.py
 */
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const REPO = path.resolve(__dirname, '../../..');
const proj = JSON.parse(fs.readFileSync(path.join(REPO, 'data/KE-enso-explorer/provenance.json'), 'utf8'));
const qmd  = fs.readFileSync(path.join(REPO, 'notebooks/KE-enso-explorer/notebook_v3.qmd'), 'utf8');

// Pull the real tab-methods + drawer markup out of the qmd, so the test runs against
// what Quarto will actually emit rather than a hand-made fixture.
const sec = qmd.slice(qmd.indexOf('<section id="tab-methods"'), qmd.indexOf('</section>', qmd.indexOf('<section id="tab-methods"')) + 10);
const drw = qmd.slice(qmd.indexOf('<div id="drawer-overlay"'), qmd.indexOf('</aside>') + 8);

const dom = new JSDOM(`<!doctype html><html><body>${sec}${drw}</body></html>`, { runScripts: 'outside-only', url: 'https://adaptationatlas.github.io/atlas_notebooks/notebooks/KE-enso-explorer/notebook_v3.html' });
const { window } = dom;
global.window = window; global.document = window.document; global.navigator = window.navigator;
global.location = window.location; global.history = window.history; global.console = console;

// stubs the notebook provides
window.switchTab = () => {};
window.filterDatasetCategory = (cat, btn) => { window.__lastCat = cat; };
window.jumpToDataset = () => {};

const src = fs.readFileSync(path.join(REPO, 'helpers/provenanceDrawer.js'), 'utf8');
window.eval(src);
window.provenanceDrawer.mount(proj);

let fails = 0;
const ok = (cond, msg) => { console.log((cond ? '  PASS ' : '  FAIL ') + msg); if (!cond) fails++; };
const D = window.document;

console.log('\n-- catalogue --');
const cards = D.querySelectorAll('.dataset-card');
ok(cards.length === proj.entries.length, `one card per entry (${cards.length}/${proj.entries.length})`);
ok(!D.getElementById('provenanceLoading'), 'loading placeholder replaced');
ok(D.getElementById('totalDatasetCount').innerText == proj.entries.length, 'total count rendered');
ok(D.querySelectorAll('#datasetCategoryFilters .filter-pill').length === 7, 'category pills generated (all + 6)');
ok(D.getElementById('provenanceCoverageBar').innerHTML.includes('Provenance not documented'), 'coverage bar shows the undocumented tally');

console.log('\n-- every notebook call site resolves --');
const calls = [...qmd.matchAll(/openMethodDrawer\('([a-z0-9_-]+)'\)/g)].map(m => m[1]);
const jumps = [...qmd.matchAll(/jumpToDataset\('([a-z0-9_-]+)'\)/g)].map(m => m[1]);
for (const k of [...new Set([...calls, ...jumps])]) {
  const resolved = window.provenanceDrawer.resolveKey(k);
  const card = D.getElementById('card-' + resolved);
  ok(!!card, `${k} -> ${resolved} (card present)`);
}

console.log('\n-- drawer: authored record (kenya-flood-gfm) --');
window.openMethodDrawer('gfm_flood');
let body = D.getElementById('drawer-body').innerHTML;
ok(D.getElementById('provenance-drawer').classList.contains('open'), 'drawer opens');
ok(body.includes('Contains modified Copernicus Emergency Management Service information [year]'), 'Copernicus attribution verbatim');
ok(body.includes('Attribution required — reproduce verbatim'), 'attribution flagged as mandatory');
ok(body.includes('255 = not observed'), 'Blank-not-Zero caveat present');
ok(body.includes('labelled by the year of their FIRST month'), 'GFM-vs-CHIRPS season-label mismatch present');
// caveats + not-recommended must not be inside a <details>
const critical = [...D.querySelectorAll('.prov-block.prov-critical')];
ok(critical.length >= 2, 'critical blocks rendered');
ok(critical.every(b => !b.closest('details')), 'caveats / not-recommended are never collapsed');
ok(body.includes('Splicing into one continuous flood time series'), 'not_recommended_for rendered');
ok(D.querySelectorAll('details.prov-fold').length > 0, 'technical detail is collapsible');
ok(location.hash === '#dataset=kenya-flood-gfm', 'deep link set');

console.log('\n-- drawer: KNBS admin trap --');
window.openMethodDrawer('kenya-population-knbs-census');
body = D.getElementById('drawer-body').innerHTML;
ok(body.includes('345 KNBS sub-county rows'), 'KNBS 345-vs-290 admin trap present');
ok(body.includes('This product was adapted from the Statistical Office of Kenya'), 'KNBS attribution verbatim');

console.log('\n-- drawer: thin record must look thin --');
window.openMethodDrawer('exposure_vop');
body = D.getElementById('drawer-body').innerHTML;
ok(body.includes('Metadata pending'), 'catalogue-only badge shown');
ok(!body.includes('Metadata authored'), 'not presented as authored');
ok(body.includes('Currency basis must stay aligned'), 'VoP currency-mismatch gap surfaced');
ok(D.getElementById('card-crop-vop-intld15').className.includes('state-catalogue-only'), 'VoP card marked unsettled');

console.log('\n-- drawer: no entry at all --');
window.openMethodDrawer('enso-driver-indices');
body = D.getElementById('drawer-body').innerHTML;
ok(body.includes('Provenance not documented'), 'undocumented renders the gap, not a blank');
window.openMethodDrawer('a_key_that_does_not_exist');
body = D.getElementById('drawer-body').innerHTML;
ok(body.includes('Provenance not documented'), 'unknown key does not silently show another dataset');
ok(!body.includes('CHIRPS'), 'no fallback to the CHIRPS record (the old bug)');

console.log('\n-- §1e: no Atlas link for non-Atlas data --');
let leaks = 0;
for (const e of proj.entries) {
  if (e.hosting === 'atlas') continue;
  for (const a of e.assets || []) {
    if ((a.https || '').includes('digital-atlas') || (a.s3 || '').includes('digital-atlas')) leaks++;
  }
}
ok(leaks === 0, 'no digital-atlas asset link on a non-Atlas dataset');

console.log('\n-- escaping --');
ok(!D.body.innerHTML.includes('<script>alert'), 'no unescaped script injection');

console.log(`\n${fails === 0 ? 'ALL PASS' : fails + ' FAILURES'}`);
process.exit(fails === 0 ? 0 : 1);
