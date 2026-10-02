/* ---------------------------------------------------------------------------
 * provenanceDrawer.js — renders the KE-ENSO Explorer provenance drawer and the
 * Section 6 master dataset catalogue from ONE generated projection.
 *
 * Contract: hazards_prototype/HANDOVER_2026-09-18_provenance-drawer-and-metadata-gaps.md §1
 *   §1a  the notebook renders from a generated projection; it never becomes a third copy
 *   §1b  `state` (metadata maturity) and `hosting` (whose bytes) are orthogonal, both rendered
 *   §1c  always-visible / never-collapsed / collapsible split
 *   §1d  the drawer and tab-methods are two views of the same projection
 *   §1e  no Atlas link for data we do not publish; `note` is never paraphrased
 *
 * This file contains NO dataset metadata. Every licence, citation, caveat, coverage and
 * attribution string on screen comes from data/KE-enso-explorer/provenance.json, which
 * _sources/provenance_build.py generates from the CDH records. The only strings here
 * describe the state machine itself.
 *
 * Mount:  window.provenanceDrawer.mount(projection)
 * Open:   openMethodDrawer('<key or legacy alias>')     // global, back-compatible
 * Link:   #dataset=<key>                                 // deep-linkable
 * ------------------------------------------------------------------------- */
(function () {
  'use strict';

  var S = { doc: null, entries: [], byKey: {}, categories: [], mounted: false, activeKey: null };

  /* -- metadata maturity. A thin record must LOOK thin. ---------------------- */
  var STATE_META = {
    'authored': {
      label: 'Metadata authored', cls: 'is-ok',
      hint: 'A CDH v0.3.0 record exists and passes strict validation.'
    },
    'draft': {
      label: 'Provisional metadata', cls: 'is-warn',
      hint: 'A CDH record exists but only passes draft validation. Fields below may be incomplete.'
    },
    'invalid': {
      label: 'Metadata does not validate', cls: 'is-bad',
      hint: 'A CDH record exists but fails both strict and draft validation. Treat everything below as unverified.'
    },
    'catalogue-only': {
      label: 'Metadata pending', cls: 'is-warn',
      hint: 'Listed in the pipeline dataset catalogue, but no outward-facing CDH record has been authored. Licence, citation and caveats are not yet established.'
    },
    'undocumented': {
      label: 'Provenance not documented', cls: 'is-bad',
      hint: 'No CDH record and no catalogue record. This dataset is used by the notebook but its provenance has not been written down anywhere.'
    }
  };

  /* -- whose bytes the reader is about to fetch ------------------------------ */
  var HOSTING_META = {
    'atlas': { label: 'Published by the Atlas', cls: 'is-neutral',
      hint: 'Held and served from s3://digital-atlas/.' },
    'federated': { label: 'External source', cls: 'is-info',
      hint: 'The record is ours; the data stays with the provider. No Atlas copy exists.' },
    'unknown': { label: 'Hosting not recorded', cls: 'is-warn',
      hint: 'No record states where these bytes are served from.' }
  };

  var CAT_FALLBACK = 'Uncategorised';

  /* ------------------------------------------------------------------ utils */

  function esc(v) {
    if (v === null || v === undefined) return '';
    return String(v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function has(a) { return Array.isArray(a) && a.length > 0; }

  function link(url, text) {
    if (!url) return esc(text || '');
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(text || url) + '</a>';
  }

  function badge(meta, extraTitle) {
    if (!meta) return '';
    return '<span class="prov-badge ' + meta.cls + '" title="' +
      esc(extraTitle ? meta.hint + ' (' + extraTitle + ')' : meta.hint) + '">' +
      esc(meta.label) + '</span>';
  }

  function stateMeta(e) { return STATE_META[e.state] || STATE_META.undocumented; }
  function hostMeta(e) { return HOSTING_META[e.hosting] || HOSTING_META.unknown; }

  function categoryLabel(id) {
    for (var i = 0; i < S.categories.length; i++) {
      if (S.categories[i].id === id) return S.categories[i].label;
    }
    return CAT_FALLBACK;
  }

  /* Resolve a key or any legacy notebook alias to an entry. Returns null rather
     than falling back to some other dataset — showing the wrong provenance is
     worse than showing none. */
  function resolve(key) {
    if (!key) return null;
    if (S.byKey[key]) return S.byKey[key];
    var real = S.doc && S.doc.aliases ? S.doc.aliases[key] : null;
    return real && S.byKey[real] ? S.byKey[real] : null;
  }

  /* --------------------------------------------------------------- drawer */

  function sectionBlock(title, bodyHtml, klass) {
    if (!bodyHtml) return '';
    return '<div class="prov-block ' + (klass || '') + '">' +
      '<h4 class="prov-block-title">' + esc(title) + '</h4>' + bodyHtml + '</div>';
  }

  function foldBlock(title, bodyHtml) {
    if (!bodyHtml) return '';
    return '<details class="prov-fold"><summary>' + esc(title) + '</summary>' +
      '<div class="prov-fold-body">' + bodyHtml + '</div></details>';
  }

  function dl(rows) {
    var out = rows.filter(function (r) { return r && r[1]; })
      .map(function (r) {
        return '<div class="prov-dl-row"><dt>' + esc(r[0]) + '</dt><dd>' + r[1] + '</dd></div>';
      }).join('');
    return out ? '<dl class="prov-dl">' + out + '</dl>' : '';
  }

  function renderLicence(e) {
    var L = e.licence || {};
    if (!L.id && !L.url && !L.attribution) {
      return '<p class="prov-missing">No licence is recorded for this dataset. ' +
        'Do not redistribute it, or assume terms, until a record is authored.</p>';
    }
    var rows = [
      ['Licence', L.url ? link(L.url, L.id || 'licence terms') : esc(L.id)],
      ['Access', L.access ? esc(L.access) + (L.access_note ? ' — ' + esc(L.access_note) : '') : '']
    ];
    var html = dl(rows);
    if (L.attribution) {
      html += '<div class="prov-attribution' + (L.attribution_verbatim_required ? ' is-required' : '') + '">' +
        '<span class="prov-attribution-label">' +
        (L.attribution_verbatim_required
          ? 'Attribution required — reproduce verbatim'
          : 'Attribution') +
        '</span><q>' + esc(L.attribution) + '</q></div>';
    } else if (L.attribution_verbatim_required) {
      html += '<p class="prov-missing">This licence mandates specific attribution wording, ' +
        'but no attribution string is recorded. Check the licence terms before republishing.</p>';
    }
    return html;
  }

  function renderProducer(e) {
    if (!has(e.producer)) return '';
    var rows = e.producer.map(function (c) {
      var who = c.organization || c.name || '';
      if (c.organization && c.name) who = c.name + ', ' + c.organization;
      var roles = has(c.roles) ? ' <span class="prov-roles">' + esc(c.roles.join(', ')) + '</span>' : '';
      return '<li>' + (c.url ? link(c.url, who) : esc(who)) + roles + '</li>';
    }).join('');
    return '<ul class="prov-list">' + rows + '</ul>';
  }

  function renderCoverage(e) {
    var C = e.coverage || {};
    return dl([
      ['Spatial', esc(C.spatial)],
      ['Temporal', esc(C.temporal)],
      ['CRS', esc(C.crs)]
    ]);
  }

  function renderCitation(e) {
    var C = e.citation;
    if (!C) return '';
    var html = C.text ? '<p class="prov-citation">' + esc(C.text) + '</p>' : '';
    if (C.url) html += '<p>' + link(C.url, C.url) + '</p>';
    if (has(C.dois)) {
      html += '<p class="prov-dois">' + C.dois.map(function (d) {
        return link('https://doi.org/' + d, d);
      }).join(' &middot; ') + '</p>';
    }
    return html;
  }

  /* Caveats: rendered verbatim, in full, never collapsed. This is where "255 =
     not observed, NOT dry", the SAR gaps, the NDJ/DJF label mismatch and the
     KNBS 345-vs-290 admin trap live. */
  function renderCaveats(e) {
    if (!has(e.caveats)) return '';
    return '<div class="prov-caveats">' + e.caveats.map(function (p) {
      return '<p>' + esc(p) + '</p>';
    }).join('') + '</div>';
  }

  function renderAvoid(e) {
    if (!has(e.avoid)) return '';
    return '<ul class="prov-avoid">' + e.avoid.map(function (a) {
      var h = '<li><strong>' + esc(a.use) + '</strong>';
      if (a.reason) h += '<span class="prov-avoid-reason">' + esc(a.reason) + '</span>';
      if (a.use_instead) h += '<span class="prov-avoid-instead">Use instead: ' + esc(a.use_instead) + '</span>';
      return h + '</li>';
    }).join('') + '</ul>';
  }

  function renderGates(e) {
    if (!has(e.gates)) return '';
    return '<ul class="prov-gates">' + e.gates.map(function (g) {
      var cls = String(g.result || '').toUpperCase() === 'PASS' ? 'is-ok' : 'is-bad';
      return '<li><span class="prov-badge ' + cls + '">' + esc(g.result) + '</span> ' +
        esc(g.name || '') + (g.value !== undefined && g.value !== null ? ' — ' + esc(g.value) : '') +
        (g.ref ? ' <span class="prov-roles">' + esc(g.ref) + '</span>' : '') + '</li>';
    }).join('') + '</ul>';
  }

  function renderGaps(e) {
    if (!has(e.gaps)) return '';
    return '<ul class="prov-gaps">' + e.gaps.map(function (g) {
      return '<li>' + esc(g) + '</li>';
    }).join('') + '</ul>';
  }

  function renderAssets(e) {
    if (!has(e.assets)) return '';
    return e.assets.map(function (a) {
      var locs = [];
      if (a.https) locs.push(link(a.https, 'HTTPS'));
      if (a.s3) locs.push('<code>' + esc(a.s3) + '</code>');
      (a.other_locations || []).forEach(function (u) { locs.push(link(u, u)); });
      return '<div class="prov-asset"><div class="prov-asset-name">' + esc(a.name) + '</div>' +
        (a.description ? '<p>' + esc(a.description) + '</p>' : '') +
        dl([
          ['Locations', locs.join(' &middot; ')],
          ['Path template', a.href_template ? '<code>' + esc(a.href_template) + '</code>' : ''],
          ['Media type', esc(a.media_type)],
          ['Size', esc(a.file_size)],
          ['NoData', a.nodata === null || a.nodata === undefined ? '' : esc(a.nodata)]
        ]) + '</div>';
    }).join('');
  }

  function renderProcessing(e) {
    if (!has(e.processing)) return '';
    return '<ol class="prov-steps">' + e.processing.map(function (p) {
      var h = '<li><span class="prov-step-id">' + esc(p.id) + '</span>';
      if (p.description) h += '<p>' + esc(p.description) + '</p>';
      if (p.code) {
        h += '<p class="prov-code">' + (p.code_url ? link(p.code_url, p.code) : '<code>' + esc(p.code) + '</code>') + '</p>';
      }
      if (has(p.derived_from)) {
        h += '<p class="prov-derived">From: ' + p.derived_from.map(function (d) {
          return link(d.url, d.title);
        }).join(' &middot; ') + '</p>';
      }
      return h + '</li>';
    }).join('') + '</ol>';
  }

  function renderTechnical(e) {
    var T = e.technical || {};
    var html = dl([
      ['Resource type', esc(T.resource_type)],
      ['CDH domain', has(T.domain) ? esc(T.domain.join(', ')) : ''],
      ['Schema version', esc(T.schema_version)],
      ['Created / updated', T.created || T.updated ? esc([T.created, T.updated].filter(Boolean).join(' → ')) : ''],
      ['Keywords', has(T.keywords) ? esc(T.keywords.join(', ')) : '']
    ]);
    if (has(T.variables)) {
      html += '<h5 class="prov-sub">Variables</h5><ul class="prov-list">' +
        T.variables.map(function (v) {
          return '<li><code>' + esc(v.name) + '</code>' +
            (v.unit ? ' <span class="prov-roles">' + esc(v.unit) + '</span>' : '') +
            (v.description ? '<br>' + esc(v.description) : '') + '</li>';
        }).join('') + '</ul>';
    }
    if (has(T.dimensions)) {
      html += '<h5 class="prov-sub">Dimensions</h5><ul class="prov-list">' +
        T.dimensions.map(function (d) {
          var n = has(d.values) ? d.values.length : 0;
          return '<li><code>' + esc(d.name) + '</code> <span class="prov-roles">' + esc(d.type) + '</span>' +
            (n ? ' — ' + n + ' values (' + esc(d.values[0]) + ' … ' + esc(d.values[n - 1]) + ')' : '') +
            (d.description ? '<br>' + esc(d.description) : '') + '</li>';
        }).join('') + '</ul>';
    }
    return html;
  }

  function renderRecordLinks(e) {
    var R = e.record || {};
    var repo = 'https://github.com/AdaptationAtlas/hazards_prototype/blob/main/';
    return dl([
      ['CDH record', R.cdh ? link(repo + R.cdh, R.cdh) : ''],
      ['Catalogue record', R.catalogue ? link(repo + R.catalogue, R.catalogue) : ''],
      ['CDH catalog', R.catalog_pr ? link(R.catalog_pr, R.catalog_pr.replace(/^.*\/pull\//, 'PR #')) +
        (R.catalog_pr_state ? ' — ' + esc(R.catalog_pr_state) : '') : ''],
      ['Published record', R.published_record ? link(R.published_record, 'cdh-catalog') : '']
    ]);
  }

  function renderNotebookUse(e) {
    var N = e.notebook || {};
    var files = has(N.files)
      ? '<ul class="prov-list">' + N.files.map(function (f) {
          return '<li><code>' + esc(f) + '</code></li>';
        }).join('') + '</ul>'
      : '';
    var related = has(N.related)
      ? '<p class="prov-related">' + N.related.map(function (k) {
          var r = resolve(k);
          return '<button type="button" class="prov-related-btn" data-prov-key="' + esc(k) + '">' +
            esc(r ? r.title : k) + '</button>';
        }).join(' ') + '</p>'
      : '';
    return dl([['Files read by this notebook', files], ['Built by', N.built_by ? '<code>' + esc(N.built_by) + '</code>' : '']]) + related;
  }

  function drawerHtml(e) {
    var sm = stateMeta(e), hm = hostMeta(e);
    var h = '';

    h += '<div class="prov-head">' +
      '<div class="prov-badges">' + badge(sm, e.state_basis) + badge(hm) + '</div>' +
      '<h3 id="drawer-title">' + esc(e.title) + '</h3>' +
      (e.title_source === 'notebook-label'
        ? '<p class="prov-title-note">Name supplied by the notebook — no metadata record provides a title for this dataset.</p>'
        : '') +
      '</div>';

    if (e.state === 'undocumented') {
      h += '<div class="prov-alert is-bad"><strong>Provenance not documented.</strong> ' +
        'This dataset is used by the notebook but has no CDH record and no catalogue entry, so its ' +
        'licence, citation and caveats have not been established. Treat every figure derived from it ' +
        'as provisional, and do not redistribute the data.</div>';
    } else if (e.state !== 'authored') {
      h += '<div class="prov-alert is-warn"><strong>' + esc(sm.label) + '.</strong> ' +
        esc(sm.hint) + '</div>';
    }

    if (e.summary) h += sectionBlock('What it is', '<p>' + esc(e.summary) + '</p>');

    h += sectionBlock('Licence and attribution', renderLicence(e));
    h += sectionBlock('Producer', renderProducer(e));
    h += sectionBlock('Coverage', renderCoverage(e));
    h += sectionBlock('How to cite', renderCitation(e));

    /* Never collapsed — the reason these fields were authored at all. */
    h += sectionBlock('Read before use', renderCaveats(e), 'prov-critical');
    h += sectionBlock('Not recommended for', renderAvoid(e), 'prov-critical');
    h += sectionBlock('Live quality gates', renderGates(e), 'prov-critical');
    h += sectionBlock('Known gaps', renderGaps(e), 'prov-critical');

    /* Collapsible — deep technical review. */
    h += foldBlock('Intended uses', has(e.intended_uses)
      ? '<ul class="prov-list">' + e.intended_uses.map(function (u) {
          return '<li>' + esc(u) + '</li>'; }).join('') + '</ul>'
      : '');
    h += foldBlock('Data assets', renderAssets(e));
    h += foldBlock('Upstream sources', has(e.upstream)
      ? '<ul class="prov-list">' + e.upstream.map(function (u) {
          return '<li>' + link(u.url, u.title) + '</li>'; }).join('') + '</ul>'
      : '');
    h += foldBlock('Processing chain', renderProcessing(e));
    h += foldBlock('Technical schema', renderTechnical(e));
    h += foldBlock('Use in this notebook', renderNotebookUse(e));
    h += foldBlock('Metadata records', renderRecordLinks(e));

    h += '<div class="prov-foot">' +
      '<button type="button" class="btn-provenance-jump" onclick="jumpToFullCatalog()">Open in the full catalogue</button>' +
      '<button type="button" class="btn-provenance-jump" data-prov-copy="' + esc(deepLink(e.key)) + '">Copy link to this record</button>' +
      '</div>';

    return h;
  }

  function deepLink(key) {
    return location.origin + location.pathname + '#dataset=' + key;
  }

  /* ------------------------------------------------------------- catalogue */

  function cardHtml(e) {
    var sm = stateMeta(e), hm = hostMeta(e);
    var L = e.licence || {};
    var search = [e.key, e.title, (e.notebook || {}).search_terms, (e.aliases || []).join(' '),
                  L.id, e.state, e.hosting].filter(Boolean).join(' ').toLowerCase();

    var h = '<article class="dataset-card prov-card state-' + esc(e.state) + '"' +
      ' id="card-' + esc(e.key) + '" data-category="' + esc(e.category || '') + '"' +
      ' data-search="' + esc(search) + '">';

    h += '<div class="dataset-header"><div>' +
      '<h3 class="dataset-name">' + esc(e.title) + '</h3>' +
      '<span class="dataset-category-tag">' + esc(categoryLabel(e.category)) + '</span>' +
      '</div><span class="dataset-producer">' +
      esc(has(e.producer) ? (e.producer.find(function (p) {
        return (p.roles || []).indexOf('producer') > -1 || (p.roles || []).indexOf('licensor') > -1;
      }) || e.producer[0]).organization || '' : '') + '</span></div>';

    h += '<div class="prov-badges">' + badge(sm, e.state_basis) + badge(hm) + '</div>';

    if (e.summary) {
      h += '<p class="dataset-desc">' + esc(e.summary) + '</p>';
    } else {
      h += '<p class="dataset-desc prov-missing">No description is recorded for this dataset.</p>';
    }

    h += '<div class="dataset-meta-grid">' +
      '<div class="meta-item"><dt>Licence</dt><dd>' +
        (L.id ? esc(L.id) : '<span class="prov-missing">not recorded</span>') + '</dd></div>' +
      '<div class="meta-item"><dt>Coverage</dt><dd>' +
        esc((e.coverage || {}).temporal || '—') + '</dd></div>' +
      '</div>';

    if (has(e.gaps)) {
      h += '<div class="prov-card-gaps"><strong>Gaps</strong>' + renderGaps(e) + '</div>';
    }

    h += '<div class="s3-bar"><span>' +
      esc(has(e.assets) && e.assets[0].s3 ? e.assets[0].s3
          : has((e.notebook || {}).files) ? e.notebook.files[0]
          : 'no published location recorded') + '</span>' +
      '<button type="button" class="copy-btn" data-prov-open="' + esc(e.key) + '">Provenance</button>' +
      '</div>';

    return h + '</article>';
  }

  function renderCoverageBar() {
    var bar = document.getElementById('provenanceCoverageBar');
    if (!bar) return;
    var tally = {};
    S.entries.forEach(function (e) { tally[e.state] = (tally[e.state] || 0) + 1; });
    var order = ['authored', 'draft', 'invalid', 'catalogue-only', 'undocumented'];
    bar.innerHTML = order.filter(function (k) { return tally[k]; }).map(function (k) {
      return '<span class="prov-coverage-item">' + badge(STATE_META[k]) +
        '<strong>' + tally[k] + '</strong></span>';
    }).join('') +
    '<span class="prov-coverage-note">Metadata state is probed against the CDH v0.3.0 schema at build time, not asserted here.</span>';
  }

  function renderFilters() {
    var counts = {};
    S.entries.forEach(function (e) { counts[e.category] = (counts[e.category] || 0) + 1; });

    var select = document.getElementById('datasetCategorySelect');
    if (select) {
      var optHtml = '<option value="all">All categories (' + S.entries.length + ' datasets)</option>';
      S.categories.forEach(function (c) {
        if (!counts[c.id]) return;
        optHtml += '<option value="' + esc(c.id) + '">' + esc(c.label) + ' (' + counts[c.id] + ')</option>';
      });
      select.innerHTML = optHtml;
    }

    var box = document.getElementById('datasetCategoryFilters');
    if (box) {
      box.innerHTML = '';
      box.style.display = 'none';
    }
  }

  function renderCatalogue() {
    var grid = document.getElementById('datasetCatalogGrid');
    if (!grid) return;
    grid.innerHTML = S.entries.map(cardHtml).join('');
    var total = document.getElementById('totalDatasetCount');
    if (total) total.innerText = S.entries.length;
    var vis = document.getElementById('visibleDatasetCount');
    if (vis) vis.innerText = S.entries.length;
  }

  /* ----------------------------------------------------------------- open */

  function ensureDrawerNodes() {
    return document.getElementById('provenance-drawer') && document.getElementById('drawer-overlay');
  }

  function openMethodDrawer(key) {
    if (!ensureDrawerNodes()) return;
    var body = document.getElementById('drawer-body');
    var e = resolve(key);
    if (!S.mounted) {
      body.innerHTML = '<div class="prov-alert is-warn">The provenance projection has not loaded yet. ' +
        'Reload the page, or rebuild <code>data/KE-enso-explorer/provenance.json</code>.</div>';
    } else if (!e) {
      /* Never fall back to another dataset's record. */
      body.innerHTML = '<div class="prov-alert is-bad"><strong>Provenance not documented.</strong> ' +
        'No entry exists for <code>' + esc(key) + '</code> in the provenance projection. ' +
        'Add it to <code>_sources/provenance_keymap.json</code> and rebuild.</div>';
    } else {
      body.innerHTML = drawerHtml(e);
      S.activeKey = e.key;
      window.activeDatasetKey = e.key;
      /* A sandboxed or opaque-origin document throws here; the drawer must still open. */
      try { history.replaceState(null, '', '#dataset=' + e.key); } catch (err) { /* no deep link */ }
    }
    document.getElementById('drawer-overlay').classList.add('open');
    document.getElementById('provenance-drawer').classList.add('open');
    document.getElementById('provenance-drawer').scrollTop = 0;
  }

  function closeDrawer() {
    var d = document.getElementById('provenance-drawer');
    var o = document.getElementById('drawer-overlay');
    if (d) d.classList.remove('open');
    if (o) o.classList.remove('open');
    if (location.hash.indexOf('#dataset=') === 0) {
      try { history.replaceState(null, '', location.pathname + location.search); } catch (err) { /* leave the hash */ }
    }
  }

  function handleHash() {
    var m = /^#dataset=(.+)$/.exec(location.hash || '');
    if (!m) return;
    var key = decodeURIComponent(m[1]);
    if (typeof window.switchTab === 'function') window.switchTab('tab-methods');
    openMethodDrawer(key);
  }

  /* --------------------------------------------------------------- wiring */

  function bind() {
    document.addEventListener('click', function (ev) {
      var t = ev.target.closest ? ev.target.closest('[data-prov-open],[data-prov-key],[data-prov-cat],[data-prov-copy]') : null;
      if (!t) return;
      if (t.hasAttribute('data-prov-open')) {
        ev.preventDefault();
        openMethodDrawer(t.getAttribute('data-prov-open'));
      } else if (t.hasAttribute('data-prov-key')) {
        ev.preventDefault();
        openMethodDrawer(t.getAttribute('data-prov-key'));
      } else if (t.hasAttribute('data-prov-cat')) {
        ev.preventDefault();
        if (typeof window.filterDatasetCategory === 'function') {
          window.filterDatasetCategory(t.getAttribute('data-prov-cat'), t);
        }
      } else if (t.hasAttribute('data-prov-copy')) {
        ev.preventDefault();
        var url = t.getAttribute('data-prov-copy');
        if (navigator.clipboard) navigator.clipboard.writeText(url);
        var was = t.innerText;
        t.innerText = 'Link copied';
        setTimeout(function () { t.innerText = was; }, 1600);
      }
    });

    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') closeDrawer();
    });

    window.addEventListener('hashchange', handleHash);
  }

  function mount(doc) {
    if (!doc || !Array.isArray(doc.entries)) {
      console.warn('provenanceDrawer: projection missing or malformed');
      return;
    }
    S.doc = doc;
    S.entries = doc.entries.slice();
    S.categories = doc.categories || [];
    S.byKey = {};
    S.entries.forEach(function (e) { S.byKey[e.key] = e; });
    S.mounted = true;

    renderCoverageBar();
    renderFilters();
    renderCatalogue();
    handleHash();
  }

  /* Legacy notebook handle -> projection key, for call sites that address the
     catalogue card directly (card-<key>). Returns the input unchanged when the
     projection has not mounted, so nothing breaks before load. */
  function resolveKey(key) {
    var e = resolve(key);
    return e ? e.key : key;
  }

  window.provenanceDrawer = {
    mount: mount, open: openMethodDrawer, close: closeDrawer, resolveKey: resolveKey, state: S
  };
  window.openMethodDrawer = openMethodDrawer;
  window.closeDrawer = closeDrawer;
  window.jumpToFullCatalog = function () {
    if (typeof window.jumpToDataset === 'function' && S.activeKey) {
      window.jumpToDataset(S.activeKey);
    } else if (typeof window.switchTab === 'function') {
      window.switchTab('tab-methods');
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }

  /* The OJS loader may resolve before or after this script parses. */
  if (window.__provenanceProjection) mount(window.__provenanceProjection);
})();
