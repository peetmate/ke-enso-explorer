/**
 * controlRegistry.js — Centralized Control Vocabulary & Tooltip Registry for ENSO Explorer v3
 * 
 * Implements §5.4 of the ENSO v3 Backlog:
 * Standardizes control labels, options, and plain-language tooltips across the notebook.
 */

export const CONTROL_VOCABULARY = {
  county: {
    label: "County",
    tooltip: "Target administrative boundary across Kenya's 47 counties"
  },
  season: {
    label: "Season",
    tooltip: "Bimodal agricultural rainfall season: MAM (Long Rains, Mar–May) or OND (Short Rains, Oct–Dec)"
  },
  driver: {
    label: "Ocean driver",
    tooltip: "Large-scale sea surface temperature teleconnection mode: Pacific ENSO (RONI) or Indian Ocean Dipole (DMI)"
  },
  years: {
    label: "Years",
    tooltip: "Historical multi-decadal observation period"
  },
  variable: {
    label: "Variable",
    tooltip: "Earth observation metric (rainfall, SPEI-3, NDVI, GFM flood, WRSI) or socio-economic indicator"
  },
  view: {
    label: "View",
    tooltip: "Display representation: Lines, Bars, Map, or Table"
  },
  measure: {
    label: "Measure",
    tooltip: "Data scale: absolute physical units, % of national, or log scale"
  },
  driverStrip: {
    label: "Ocean-state markers",
    tooltip: "Color-coded bar indicating historical El Niño, La Niña, or Neutral states"
  },
  spatialSpread: {
    label: "Between-sub-county variation",
    tooltip: "Range of variation across sub-counties within the selected county boundary"
  },
  phaseIntensity: {
    label: "Ocean-state strength",
    tooltip: "Anomaly magnitude threshold (|z| ≥ 1.0σ moderate, |z| ≥ 1.5σ strong/extreme)"
  },
  sourcesMethods: {
    label: "Sources & methods",
    tooltip: "Open dataset provenance and scientific methodology drawer"
  }
};

/**
 * Returns HTML string for an accessible, keyboard-focusable plain-language tooltip.
 * @param {string} text - Tooltip text explaining the technical term
 * @returns {string} HTML markup string
 */
export function renderTooltip(text) {
  if (!text) return "";
  const esc = String(text).replace(/"/g, '&quot;');
  return `<span class="enso-tooltip-wrap">
    <span class="enso-tooltip-icon" tabindex="0" role="tooltip" aria-label="${esc}">?</span>
    <span class="enso-tooltip-bubble">${esc}</span>
  </span>`;
}

/**
 * Returns formatted HTML label with an optional tooltip icon.
 * @param {string} key - Vocabulary key (e.g. 'county', 'driver', 'measure')
 * @param {boolean} [withTooltip=true] - Whether to append tooltip
 * @returns {string} Formatted label string
 */
export function controlLabel(key, withTooltip = true) {
  const item = CONTROL_VOCABULARY[key];
  if (!item) return key;
  if (!withTooltip || !item.tooltip) return item.label;
  return `${item.label} ${renderTooltip(item.tooltip)}`;
}

/**
 * Returns plain-text label string without tooltip markup.
 * @param {string} key - Vocabulary key
 * @returns {string} Plain text label
 */
export function getLabelText(key) {
  const item = CONTROL_VOCABULARY[key];
  return item ? item.label : key;
}

/**
 * Render empty, loading, or error placeholder HTML
 * @param {object} opts
 * @param {'loading'|'empty'|'error'} opts.type
 * @param {string} opts.title
 * @param {string} [opts.message]
 * @returns {string} HTML markup
 */
export function renderStatePlaceholder({ type = "loading", title = "", message = "" } = {}) {
  const t = String(title || "");
  const m = String(message || "");
  if (type === "loading") {
    return `<div class="enso-state-container enso-loading-state" role="status" aria-live="polite">
      <div class="enso-loading-spinner" aria-hidden="true"></div>
      <div style="font-weight: 600; color: #1e293b;">${t || "Loading data..."}</div>
      ${m ? `<div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">${m}</div>` : ""}
    </div>`;
  }
  if (type === "error") {
    return `<div class="enso-state-container enso-error-state" role="alert">
      <div style="font-weight: 700; color: #991b1b; margin-bottom: 4px;">⚠️ ${t || "Unable to display visualization"}</div>
      <div style="font-size: 0.8rem; color: #b91c1c;">${m || "A data loading or rendering error occurred."}</div>
    </div>`;
  }
  return `<div class="enso-state-container enso-empty-state" role="status">
    <strong>${t || "No data available"}</strong>
    <div>${m || "No observations or records match the selected parameters."}</div>
  </div>`;
}

// Global window registration for non-module contexts
if (typeof window !== "undefined") {
  window.ensoUI = {
    CONTROL_VOCABULARY,
    renderTooltip,
    controlLabel,
    getLabelText,
    renderStatePlaceholder
  };
}
