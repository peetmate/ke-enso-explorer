/**
 * Glossary Tooltip and Modal Interactivity Helper
 * Automatically scans elements marked with class .enso-glossary-term or [data-glossary-term]
 * and provides rich interactive tooltips and click modals with formal definitions,
 * LaTeX formulas, and links to the citable methods monograph.
 */
(function () {
  'use strict';

  var GLOSSARY_PATH = '/data/KE-enso-explorer/glossary.json';
  var glossaryTerms = {};
  var tooltipEl = null;

  function loadGlossary() {
    // Check if relative path needs adjustment based on current location
    var fetchUrl = GLOSSARY_PATH;
    if (window.location.pathname.indexOf('/notebooks/') !== -1) {
      fetchUrl = '../../data/KE-enso-explorer/glossary.json';
    }

    fetch(fetchUrl)
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data && data.terms) {
          data.terms.forEach(function (t) {
            var key = (t.abbreviation || t.term).toLowerCase();
            glossaryTerms[key] = t;
            glossaryTerms[t.term.toLowerCase()] = t;
          });
          initGlossaryInteractivity();
        }
      })
      .catch(function (err) {
        // Silent failover if offline
        console.warn('Could not load glossary terms:', err);
      });
  }

  function getTooltipEl() {
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.id = 'enso-glossary-tooltip';
      tooltipEl.setAttribute('role', 'tooltip');
      tooltipEl.style.cssText =
        'position: absolute; z-index: 99999; display: none; max-width: 340px; ' +
        'background: #1e293b; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; ' +
        'font-size: 0.8rem; line-height: 1.45; padding: 10px 14px; border-radius: 6px; ' +
        'box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -6px rgba(0, 0, 0, 0.3); ' +
        'border: 1px solid #334155; pointer-events: none; transition: opacity 0.15s ease;';
      document.body.appendChild(tooltipEl);
    }
    return tooltipEl;
  }

  function showTooltip(e, termData) {
    var tip = getTooltipEl();
    var abbr = termData.abbreviation ? ' (' + termData.abbreviation + ')' : '';
    var formula = termData.formula_or_metric ? '<div style="margin-top:5px; font-family:monospace; background:rgba(255,255,255,0.1); padding:2px 6px; border-radius:3px; color:#38bdf8; font-size:0.75rem;">' + escapeHtml(termData.formula_or_metric) + '</div>' : '';

    tip.innerHTML =
      '<div style="font-weight:700; color:#38bdf8; margin-bottom:3px; font-size:0.85rem;">' + escapeHtml(termData.term) + abbr + '</div>' +
      '<div style="color:#cbd5e1; font-size:0.72rem; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px; font-weight:600;">' + escapeHtml(termData.category) + '</div>' +
      '<div style="color:#e2e8f0;">' + escapeHtml(termData.tooltip || termData.definition) + '</div>' +
      formula;

    tip.style.display = 'block';
    tip.style.opacity = '1';

    positionTooltip(e, tip);
  }

  function positionTooltip(e, tip) {
    var x = e.pageX + 12;
    var y = e.pageY + 12;

    // Check viewport bounds
    var tipWidth = tip.offsetWidth;
    var tipHeight = tip.offsetHeight;
    var docWidth = document.documentElement.clientWidth;

    if (x + tipWidth > window.scrollX + docWidth - 20) {
      x = e.pageX - tipWidth - 12;
    }

    tip.style.left = Math.max(10, x) + 'px';
    tip.style.top = y + 'px';
  }

  function hideTooltip() {
    if (tooltipEl) {
      tooltipEl.style.opacity = '0';
      tooltipEl.style.display = 'none';
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function initGlossaryInteractivity() {
    var targets = document.querySelectorAll('.enso-glossary-term, [data-glossary-term]');
    targets.forEach(function (el) {
      var termKey = (el.getAttribute('data-glossary-term') || el.textContent || '').trim().toLowerCase();
      var termData = glossaryTerms[termKey];
      if (termData) {
        el.style.borderBottom = '1px dotted #0284c7';
        el.style.cursor = 'help';
        el.addEventListener('mouseenter', function (e) {
          showTooltip(e, termData);
        });
        el.addEventListener('mousemove', function (e) {
          positionTooltip(e, getTooltipEl());
        });
        el.addEventListener('mouseleave', hideTooltip);
      }
    });
  }

  // Expose global helper for programmatic tooltips or lookups
  window.ensoGlossary = {
    lookup: function (key) {
      return glossaryTerms[(key || '').toLowerCase()];
    },
    refresh: initGlossaryInteractivity
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadGlossary);
  } else {
    loadGlossary();
  }
})();
