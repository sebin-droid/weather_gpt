// =============================================
// NDVI VEGETATION ANALYSIS — Tab Logic
// =============================================

const NDVI_BACKEND = "http://127.0.0.1:8000";

const ndviDate = document.getElementById('ndvi-date');
const ndviAnalyzeBtn = document.getElementById('ndvi-analyze-btn');
const ndviClearBtn = document.getElementById('ndvi-clear-btn');
const ndviLoading = document.getElementById('ndvi-loading');
const ndviResults = document.getElementById('ndvi-results');

let drawnPolygon = null;
let drawControl = null;

// Default date: ~10 days ago (MODIS has data processing lag)
const tenDaysAgo = new Date();
tenDaysAgo.setDate(tenDaysAgo.getDate() - 10);
ndviDate.value = tenDaysAgo.toISOString().slice(0, 10);


// =============================================
// Drawing controls (enable/disable with tab)
// =============================================

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
      polyline: false,
      rectangle: {
        shapeOptions: { color: '#22c55e', weight: 2, fillOpacity: 0.15 }
      },
      circle: false,
      circlemarker: false,
      marker: false
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


// =============================================
// Analyze button
// =============================================

ndviAnalyzeBtn.addEventListener('click', async () => {
  if (!drawnPolygon) {
    alert('Please draw a polygon on the map first.');
    return;
  }

  // Get polygon coordinates
  const latlngs = drawnPolygon.getLatLngs()[0];
  const polygon = latlngs.map(ll => [ll.lat, ll.lng]);
  const date = ndviDate.value;

  ndviLoading.classList.remove('hidden');
  ndviResults.classList.add('hidden');
  ndviAnalyzeBtn.disabled = true;

  try {
    const resp = await fetch(`${NDVI_BACKEND}/ndvi/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ polygon, date })
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'NDVI analysis failed');
    }

    const data = await resp.json();
    ndviLoading.classList.add('hidden');

    // Draw NDVI grid on map
    if (window.drawNDVI) window.drawNDVI(data);

    // Render results panel
    renderNDVIResults(data);

  } catch (err) {
    ndviLoading.classList.add('hidden');
    ndviResults.innerHTML = `<div class="error-msg">❌ ${err.message}</div>`;
    ndviResults.classList.remove('hidden');
  } finally {
    ndviAnalyzeBtn.disabled = false;
  }
});


// =============================================
// Clear button
// =============================================

ndviClearBtn.addEventListener('click', () => {
  if (window.mapDrawnItems) window.mapDrawnItems.clearLayers();
  if (window.drawNDVI) window.drawNDVI({ grid: [] });
  drawnPolygon = null;
  ndviAnalyzeBtn.disabled = true;
  ndviResults.classList.add('hidden');
});


// =============================================
// Render NDVI results
// =============================================

function renderNDVIResults(data) {
  const healthColors = {
    'healthy': '#22c55e',
    'moderate': '#eab308',
    'poor': '#f97316',
    'very_poor': '#ef4444'
  };

  const breakdown = data.breakdown || {};
  let breakdownHTML = Object.entries(breakdown)
    .filter(([cat]) => cat !== 'no_data')
    .map(([cat, pct]) => {
      const color = healthColors[cat] || '#999';
      const label = cat.replace('_', ' ');
      return `<div class="ndvi-bar">
        <span class="ndvi-bar-label">${label}</span>
        <div class="ndvi-bar-track"><div class="ndvi-bar-fill" style="width:${pct}%;background:${color}"></div></div>
        <span class="ndvi-bar-pct">${pct}%</span>
      </div>`;
    }).join('');

  ndviResults.innerHTML = `
    <h3>🌱 Vegetation Health Report</h3>
    <div class="ndvi-summary-grid">
      <div class="ndvi-stat"><span class="stat-label">Area</span><span class="stat-value">${data.area_hectares?.toFixed(1) || '?'} ha</span></div>
      <div class="ndvi-stat"><span class="stat-label">Avg NDVI</span><span class="stat-value">${data.average_ndvi?.toFixed(3) || 'N/A'}</span></div>
      <div class="ndvi-stat"><span class="stat-label">Overall</span><span class="stat-value" style="color:${healthColors[data.health] || '#333'};font-weight:bold">${(data.health || 'N/A').replace('_', ' ')}</span></div>
    </div>
    <div class="ndvi-breakdown">${breakdownHTML}</div>
    <div class="ndvi-explanation">${data.explanation || ''}</div>
    <div class="ndvi-legend">
      <span style="color:#22c55e">🟢 Healthy (&gt;0.6)</span>
      <span style="color:#eab308">🟡 Moderate (0.4-0.6)</span>
      <span style="color:#f97316">🟠 Poor (0.2-0.4)</span>
      <span style="color:#ef4444">🔴 Very Poor (&lt;0.2)</span>
    </div>
  `;
  ndviResults.classList.remove('hidden');
}


// =============================================
// Tab switching (called from index.html buttons)
// =============================================

window.switchTab = function (tabName) {
  // Update tab buttons
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  const btnEl = document.querySelector(`[data-tab="${tabName}"]`);
  if (btnEl) btnEl.classList.add('active');

  // Update tab content
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  const tabEl = document.getElementById(`tab-${tabName}`);
  if (tabEl) tabEl.classList.add('active');

  // Enable/disable drawing tools based on tab
  if (tabName === 'vegetation') {
    enableDrawing();
  } else {
    disableDrawing();
  }

  // Resize map after tab switch
  setTimeout(() => {
    if (window.leafletMap) window.leafletMap.invalidateSize();
  }, 100);
};
