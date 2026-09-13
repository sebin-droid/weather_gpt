// ============================================================
// ndvi.js — NDVI Vegetation Analysis tab logic
// API call, polygon handling, NDVI calculation, draw controls:
// ALL UNCHANGED.
// UI changes: renderNDVIResults uses new CSS classes and
// legend structure; switchTab updated to also manage mobile
// nav active state and set data-view on .app-body.
// ============================================================

const NDVI_BACKEND = "http://127.0.0.1:8000";

const ndviDate       = document.getElementById('ndvi-date');
const ndviAnalyzeBtn = document.getElementById('ndvi-analyze-btn');
const ndviClearBtn   = document.getElementById('ndvi-clear-btn');
const ndviLoading    = document.getElementById('ndvi-loading');
const ndviResults    = document.getElementById('ndvi-results');

let drawnPolygon = null;
let drawControl  = null;

// Default date: ~10 days ago (MODIS data lag) — UNCHANGED
const tenDaysAgo = new Date();
tenDaysAgo.setDate(tenDaysAgo.getDate() - 10);
ndviDate.value = tenDaysAgo.toISOString().slice(0, 10);


// ── Drawing controls (UNCHANGED) ─────────────────────────────
function enableDrawing() {
  if (drawControl) return;

  const drawnItems = window.mapDrawnItems;
  if (!drawnItems) return;

  drawControl = new L.Control.Draw({
    draw: {
      polygon: {
        allowIntersection: false,
        shapeOptions: { color: '#22c55e', weight: 2, fillOpacity: 0.15 }
      },
      polyline:     false,
      rectangle:    { shapeOptions: { color: '#22c55e', weight: 2, fillOpacity: 0.15 } },
      circle:       false,
      circlemarker: false,
      marker:       false
    },
    edit: {
      featureGroup: drawnItems,
      remove: true
    }
  });
  window.leafletMap.addControl(drawControl);

  window.leafletMap.on(L.Draw.Event.CREATED, function (e) {
    drawnItems.clearLayers();
    drawnItems.addLayer(e.layer);
    drawnPolygon = e.layer;
    ndviAnalyzeBtn.disabled = false;
  });

  window.leafletMap.on(L.Draw.Event.DELETED, function () {
    drawnPolygon = null;
    ndviAnalyzeBtn.disabled = true;
  });
}

function disableDrawing() {
  if (drawControl) {
    window.leafletMap.removeControl(drawControl);
    drawControl = null;
  }
}


// ── Analyze button (UNCHANGED) ───────────────────────────────
ndviAnalyzeBtn.addEventListener('click', async function () {
  if (!drawnPolygon) {
    alert('Please draw a polygon on the map first.');
    return;
  }

  const latlngs = drawnPolygon.getLatLngs()[0];
  const polygon = latlngs.map(function (ll) { return [ll.lat, ll.lng]; });
  const date    = ndviDate.value;

  ndviLoading.classList.remove('hidden');
  ndviResults.classList.add('hidden');
  ndviAnalyzeBtn.disabled = true;

  try {
    const resp = await fetch(NDVI_BACKEND + '/ndvi/analyze', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ polygon: polygon, date: date })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'NDVI analysis failed');
    }

    const data = await resp.json();
    ndviLoading.classList.add('hidden');

    if (window.drawNDVI) window.drawNDVI(data);
    renderNDVIResults(data);

  } catch (err) {
    ndviLoading.classList.add('hidden');
    ndviResults.innerHTML =
      '<div class="error-msg">Satellite data is temporarily unavailable. Please try again later.</div>';
    ndviResults.classList.remove('hidden');
    console.error('NDVI error:', err);
  } finally {
    ndviAnalyzeBtn.disabled = false;
  }
});


// ── Clear button (UNCHANGED) ─────────────────────────────────
ndviClearBtn.addEventListener('click', function () {
  if (window.mapDrawnItems) window.mapDrawnItems.clearLayers();
  if (window.drawNDVI)      window.drawNDVI({ grid: [] });
  drawnPolygon = null;
  ndviAnalyzeBtn.disabled = true;
  ndviResults.classList.add('hidden');
});


// ── Render NDVI results (UI-only change) ─────────────────────
function renderNDVIResults(data) {
  const healthColors = {
    'healthy':   '#22c55e',
    'moderate':  '#eab308',
    'poor':      '#f97316',
    'very_poor': '#ef4444'
  };

  const breakdown    = data.breakdown || {};
  const areaHa       = data.area_hectares   ? data.area_hectares.toFixed(1)   : '—';
  const avgNDVI      = data.average_ndvi    ? data.average_ndvi.toFixed(3)    : '—';
  const health       = data.health          ? data.health.replace('_', ' ')   : '—';
  const healthColor  = healthColors[data.health] || 'var(--text-1)';
  const explanation  = data.explanation || '';

  const breakdownHTML = Object.entries(breakdown)
    .filter(function (pair) { return pair[0] !== 'no_data'; })
    .map(function (pair) {
      const cat   = pair[0];
      const pct   = pair[1];
      const color = healthColors[cat] || '#999';
      const label = cat.replace('_', ' ');
      return '<div class="ndvi-bar">' +
        '<span class="ndvi-bar-label">' + label + '</span>' +
        '<div class="ndvi-bar-track">' +
          '<div class="ndvi-bar-fill" style="width:' + pct + '%;background:' + color + '"></div>' +
        '</div>' +
        '<span class="ndvi-bar-pct">' + pct + '%</span>' +
      '</div>';
    }).join('');

  ndviResults.innerHTML =
    '<h3>Vegetation Health Report</h3>' +
    '<div class="ndvi-summary-grid">' +
      '<div class="ndvi-stat"><span class="stat-label">Area</span><span class="stat-value">' + areaHa + ' ha</span></div>' +
      '<div class="ndvi-stat"><span class="stat-label">Avg NDVI</span><span class="stat-value">' + avgNDVI + '</span></div>' +
      '<div class="ndvi-stat"><span class="stat-label">Overall</span><span class="stat-value" style="color:' + healthColor + '">' + health + '</span></div>' +
    '</div>' +
    '<div class="ndvi-breakdown">' + breakdownHTML + '</div>' +
    (explanation ? '<div class="ndvi-explanation">' + explanation + '</div>' : '') +
    '<div class="ndvi-legend">' +
      '<span class="ndvi-legend-item"><span class="ndvi-legend-dot" style="background:#22c55e"></span>Healthy (&gt;0.6)</span>' +
      '<span class="ndvi-legend-item"><span class="ndvi-legend-dot" style="background:#eab308"></span>Moderate (0.4-0.6)</span>' +
      '<span class="ndvi-legend-item"><span class="ndvi-legend-dot" style="background:#f97316"></span>Poor (0.2-0.4)</span>' +
      '<span class="ndvi-legend-item"><span class="ndvi-legend-dot" style="background:#ef4444"></span>Very Poor (&lt;0.2)</span>' +
    '</div>';

  ndviResults.classList.remove('hidden');
}


// ── Tab switching — extended for mobile nav + data-view ──────
// Logic preserved: drawing enable/disable, map invalidateSize.
// UI additions: mobile nav active state, data-view attribute.
window.switchTab = function (tabName) {
  // Desktop nav tabs
  document.querySelectorAll('.tab-btn').forEach(function (b) {
    b.classList.remove('active');
  });
  var desktopBtn = document.querySelector('.tab-btn[data-tab="' + tabName + '"]');
  if (desktopBtn) desktopBtn.classList.add('active');

  // Mobile nav buttons (UI addition)
  document.querySelectorAll('.mobile-nav-btn').forEach(function (b) {
    b.classList.remove('active');
  });
  var mobileBtn = document.querySelector('.mobile-nav-btn[data-tab="' + tabName + '"]');
  if (mobileBtn) mobileBtn.classList.add('active');

  // Tab content panels
  document.querySelectorAll('.tab-content').forEach(function (t) {
    t.classList.remove('active');
  });
  var tabEl = document.getElementById('tab-' + tabName);
  if (tabEl) tabEl.classList.add('active');

  // Set data-view for CSS layout ratios (UI addition)
  var appBody = document.querySelector('.app-body');
  if (appBody) appBody.setAttribute('data-view', tabName);

  // Drawing tools (UNCHANGED)
  if (tabName === 'vegetation') {
    enableDrawing();
  } else {
    disableDrawing();
  }

  // Map resize (UNCHANGED)
  setTimeout(function () {
    if (window.leafletMap) window.leafletMap.invalidateSize();
  }, 150);
};
