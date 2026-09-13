// ============================================================
// route.js — Route Weather tab logic
// API call, URL, request/response format, route calculation:
// ALL UNCHANGED.
// UI changes: renderRouteSummary and renderRouteZones use
// new CSS classes; loading/error presentation improved.
// ============================================================

const ROUTE_BACKEND = "http://127.0.0.1:8000";

const routeOrigin  = document.getElementById('route-origin');
const routeDest    = document.getElementById('route-dest');
const routeTime    = document.getElementById('route-time');
const routeBtn     = document.getElementById('route-btn');
const routeLoading = document.getElementById('route-loading');
const routeSummary = document.getElementById('route-summary');
const routeZones   = document.getElementById('route-zones');

// Set default departure time to now (UNCHANGED)
const now = new Date();
routeTime.value = now.toISOString().slice(0, 16);

// ── Route fetch (UNCHANGED) ──────────────────────────────────
routeBtn.addEventListener('click', async function () {
  const origin    = routeOrigin.value.trim();
  const dest      = routeDest.value.trim();
  const startTime = routeTime.value;

  if (!origin || !dest) {
    alert('Please enter both origin and destination cities.');
    return;
  }

  routeLoading.classList.remove('hidden');
  routeSummary.classList.add('hidden');
  routeZones.classList.add('hidden');
  routeBtn.disabled = true;

  // UI: update button label while loading
  var origHTML = routeBtn.innerHTML;
  routeBtn.innerHTML = routeBtn.innerHTML.replace(/Get Route Weather/, 'Loading...');

  try {
    const url  = `${ROUTE_BACKEND}/route/weather?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(dest)}&start_time=${encodeURIComponent(startTime)}`;
    const resp = await fetch(url);

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || 'Route calculation failed');
    }

    const data = await resp.json();
    routeLoading.classList.add('hidden');

    if (window.drawRoute) window.drawRoute(data);

    renderRouteSummary(data);
    renderRouteZones(data.zones || []);

  } catch (err) {
    routeLoading.classList.add('hidden');
    // User-friendly error presentation (UI-only)
    routeSummary.innerHTML =
      '<div class="error-msg">Route data is temporarily unavailable. Please check city names and try again.</div>';
    routeSummary.classList.remove('hidden');
    console.error('Route error:', err);
  } finally {
    routeBtn.disabled = false;
    routeBtn.innerHTML = origHTML;
  }
});


// ── Render summary panel (UI-only change) ────────────────────
function renderRouteSummary(data) {
  const summary   = data.summary || {};
  const warnings  = summary.warnings || [];
  const breakdown = summary.weather_breakdown || {};

  const breakdownHTML = Object.entries(breakdown)
    .sort(function (a, b) { return b[1] - a[1]; })
    .map(function (pair) {
      return '<span class="weather-chip">' + pair[0] + ': ' + pair[1] + '%</span>';
    })
    .join('');

  const warningsHTML = warnings.length > 0
    ? warnings.map(function (w) { return '<div class="route-warning">' + w + '</div>'; }).join('')
    : '<div class="route-no-warning">No severe weather warnings along this route.</div>';

  const origin      = (data.origin && data.origin.city)      || '';
  const destination = (data.destination && data.destination.city) || '';
  const distKm      = data.total_distance_km  ? data.total_distance_km.toFixed(0)  : '—';
  const durationHrs = data.total_duration_hours ? data.total_duration_hours.toFixed(1) : '—';
  const departure   = data.start_time    ? new Date(data.start_time).toLocaleString()   : '—';
  const arrival     = data.arrival_time  ? new Date(data.arrival_time).toLocaleString() : '—';

  routeSummary.innerHTML =
    '<div class="summary-header">' +
      '<h3>' + origin + ' &rarr; ' + destination + '</h3>' +
    '</div>' +
    '<div class="summary-stats">' +
      '<div class="stat"><span class="stat-label">Distance</span><span class="stat-value">' + distKm + ' km</span></div>' +
      '<div class="stat"><span class="stat-label">Travel Time</span><span class="stat-value">' + durationHrs + ' hrs</span></div>' +
      '<div class="stat"><span class="stat-label">Departure</span><span class="stat-value">' + departure + '</span></div>' +
      '<div class="stat"><span class="stat-label">Arrival</span><span class="stat-value">' + arrival + '</span></div>' +
    '</div>' +
    (breakdownHTML ? '<div class="summary-breakdown">' + breakdownHTML + '</div>' : '') +
    '<div class="summary-warnings">' + warningsHTML + '</div>';

  routeSummary.classList.remove('hidden');
}


// ── Render zone cards (UI-only change) ───────────────────────
function renderRouteZones(zones) {
  if (!zones || zones.length === 0) {
    routeZones.classList.add('hidden');
    return;
  }

  const zonesHTML = zones.map(function (zone) {
    const fromCity  = zone.from_city  || '?';
    const toCity    = zone.to_city    || '?';
    const icon      = zone.weather_icon || '';
    const temp      = (zone.weather && zone.weather.temperature != null) ? zone.weather.temperature + '\u00B0C' : 'N/A';
    const precip    = (zone.weather && zone.weather.precipitation != null) ? zone.weather.precipitation + ' mm' : '0 mm';
    const wind      = (zone.weather && zone.weather.wind_speed != null)    ? zone.weather.wind_speed + ' km/h'  : 'N/A';
    const arrTime   = zone.arrival_time ? new Date(zone.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'N/A';
    const distKm    = zone.distance_km  ? zone.distance_km.toFixed(0) + ' km' : '?';
    const condition = zone.weather ? (zone.weather.condition || 'Unknown') : 'Unknown';
    const borderClr = zone.color || 'var(--border)';

    return '<div class="zone-card" style="border-left-color:' + borderClr + '">' +
      '<div class="zone-header">' +
        '<span class="zone-icon">' + icon + '</span>' +
        '<span class="zone-cities">' + fromCity + ' &rarr; ' + toCity + '</span>' +
      '</div>' +
      '<div class="zone-details">' +
        '<span>' + temp + '</span>' +
        '<span>' + precip + ' rain</span>' +
        '<span>' + wind + '</span>' +
        '<span>ETA ' + arrTime + '</span>' +
        '<span>' + distKm + '</span>' +
      '</div>' +
      '<div class="zone-condition">' + condition + '</div>' +
    '</div>';
  }).join('');

  routeZones.innerHTML = '<h3>Weather Zones Along Route</h3>' + zonesHTML;
  routeZones.classList.remove('hidden');
}
