// =============================================
// ROUTE WEATHER — Tab Logic
// =============================================

const ROUTE_BACKEND = "http://127.0.0.1:8000";

const routeOrigin = document.getElementById('route-origin');
const routeDest = document.getElementById('route-dest');
const routeTime = document.getElementById('route-time');
const routeBtn = document.getElementById('route-btn');
const routeLoading = document.getElementById('route-loading');
const routeSummary = document.getElementById('route-summary');
const routeZones = document.getElementById('route-zones');

// Set default departure time to now
const now = new Date();
routeTime.value = now.toISOString().slice(0, 16);

routeBtn.addEventListener('click', async () => {
  const origin = routeOrigin.value.trim();
  const dest = routeDest.value.trim();
  const startTime = routeTime.value;

  if (!origin || !dest) {
    alert('Please enter both origin and destination cities.');
    return;
  }

  // Show loading
  routeLoading.classList.remove('hidden');
  routeSummary.classList.add('hidden');
  routeZones.classList.add('hidden');
  routeBtn.disabled = true;
  routeBtn.textContent = '⏳ Loading...';

  try {
    const url = `${ROUTE_BACKEND}/route/weather?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(dest)}&start_time=${encodeURIComponent(startTime)}`;
    const resp = await fetch(url);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Route calculation failed');
    }

    const data = await resp.json();
    routeLoading.classList.add('hidden');

    // Draw route on map
    if (window.drawRoute) window.drawRoute(data);

    // Render summary panel
    renderRouteSummary(data);

    // Render zone cards
    renderRouteZones(data.zones || []);

  } catch (err) {
    routeLoading.classList.add('hidden');
    routeSummary.innerHTML = `<div class="error-msg">❌ ${err.message}</div>`;
    routeSummary.classList.remove('hidden');
  } finally {
    routeBtn.disabled = false;
    routeBtn.textContent = '🗺️ Get Route Weather';
  }
});


function renderRouteSummary(data) {
  const summary = data.summary || {};
  const warnings = summary.warnings || [];
  const breakdown = summary.weather_breakdown || {};

  let breakdownHTML = Object.entries(breakdown)
    .sort((a, b) => b[1] - a[1])
    .map(([condition, pct]) => `<span class="weather-chip">${condition}: ${pct}%</span>`)
    .join(' ');

  let warningsHTML = warnings.length > 0
    ? warnings.map(w => `<div class="route-warning">${w}</div>`).join('')
    : '<div class="route-no-warning">✅ No severe weather warnings along this route.</div>';

  routeSummary.innerHTML = `
    <div class="summary-header">
      <h3>🚗 ${data.origin?.city || ''} → ${data.destination?.city || ''}</h3>
    </div>
    <div class="summary-stats">
      <div class="stat"><span class="stat-label">Distance</span><span class="stat-value">${data.total_distance_km?.toFixed(0) || '?'} km</span></div>
      <div class="stat"><span class="stat-label">Travel Time</span><span class="stat-value">${data.total_duration_hours?.toFixed(1) || '?'} hrs</span></div>
      <div class="stat"><span class="stat-label">Departure</span><span class="stat-value">${data.start_time ? new Date(data.start_time).toLocaleString() : 'N/A'}</span></div>
      <div class="stat"><span class="stat-label">Arrival</span><span class="stat-value">${data.arrival_time ? new Date(data.arrival_time).toLocaleString() : 'N/A'}</span></div>
    </div>
    <div class="summary-breakdown">${breakdownHTML}</div>
    <div class="summary-warnings">${warningsHTML}</div>
  `;
  routeSummary.classList.remove('hidden');
}


function renderRouteZones(zones) {
  if (zones.length === 0) {
    routeZones.classList.add('hidden');
    return;
  }

  let zonesHTML = zones.map(zone => `
    <div class="zone-card" style="border-left: 4px solid ${zone.color || '#999'}">
      <div class="zone-header">
        <span class="zone-icon">${zone.weather_icon || '🌤'}</span>
        <span class="zone-cities">${zone.from_city || '?'} → ${zone.to_city || '?'}</span>
      </div>
      <div class="zone-details">
        <span>🌡 ${zone.weather?.temperature ?? 'N/A'}°C</span>
        <span>💧 ${zone.weather?.precipitation ?? 0} mm</span>
        <span>💨 ${zone.weather?.wind_speed ?? 'N/A'} km/h</span>
        <span>🕐 ${zone.arrival_time ? new Date(zone.arrival_time).toLocaleTimeString() : 'N/A'}</span>
        <span>📏 ${zone.distance_km?.toFixed(0) || '?'} km</span>
      </div>
      <div class="zone-condition">${zone.weather?.condition || 'Unknown'}</div>
    </div>
  `).join('');

  routeZones.innerHTML = `<h3>🗺️ Weather Zones Along Route</h3>${zonesHTML}`;
  routeZones.classList.remove('hidden');
}
