// map.js — Interactive Map for WeatherGPT
// Extended with Route, Boundary, and NDVI layers

const MAP_BACKEND_URL = "http://127.0.0.1:8000";

// =============================================
// MAP INITIALIZATION
// =============================================

let map = L.map('map').setView([10.0, 76.3], 6);
let marker = null;

// Layer groups for different features
let routeLayerGroup = L.layerGroup().addTo(map);
let boundaryLayerGroup = L.layerGroup().addTo(map);
let ndviLayerGroup = L.layerGroup().addTo(map);
let drawnItems = new L.FeatureGroup().addTo(map);

// Tile layer
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Layer control (toggle on/off)
L.control.layers(null, {
  'Route Weather': routeLayerGroup,
  'Boundaries': boundaryLayerGroup,
  'Vegetation (NDVI)': ndviLayerGroup
}, { collapsed: true, position: 'topright' }).addTo(map);


// =============================================
// EXISTING: updateMap for chat markers
// Called from chat.js whenever a location is found
// location = { city, country, latitude, longitude }
// =============================================

window.updateMap = function (location) {
    const lat = location.latitude;
    const lon = location.longitude;

    // Move map view to the city
    map.setView([lat, lon], 9);

    // Remove old marker if one exists
    if (marker) {
        map.removeLayer(marker);
    }

    // Drop a new pin with a popup
    marker = L.marker([lat, lon])
        .addTo(map)
        .bindPopup(`${location.city}, ${location.country || ""}`)
        .openPopup();

    // Also try to show boundary polygon
    fetchAndShowBoundary(location.city);
};


// =============================================
// BOUNDARY: Fetch and display admin polygon
// =============================================

async function fetchAndShowBoundary(city) {
  try {
    const resp = await fetch(`${MAP_BACKEND_URL}/boundary?city=${encodeURIComponent(city)}`);
    if (!resp.ok) return;
    const data = await resp.json();
    if (!data.geojson) return;

    boundaryLayerGroup.clearLayers();

    const geoLayer = L.geoJSON(data.geojson, {
      style: {
        fillColor: data.fill_color || '#3b82f6',
        fillOpacity: 0.25,
        color: data.fill_color || '#3b82f6',
        weight: 2
      }
    }).bindPopup(
      `<div style="min-width:150px">` +
      `<b>${data.city || city}</b>` +
      (data.boundary_type ? `<br><small>${data.boundary_type}</small>` : '') +
      (data.weather ? `<hr style="margin:4px 0">🌡 ${data.weather.temperature}°C<br>${data.weather.condition}` : '') +
      `</div>`
    );

    boundaryLayerGroup.addLayer(geoLayer);
    map.fitBounds(geoLayer.getBounds(), { padding: [20, 20] });
  } catch (e) {
    console.log('Boundary fetch failed:', e);
  }
}


// =============================================
// ROUTE: Draw route with colored weather zones
// =============================================

window.drawRoute = function (routeData) {
  routeLayerGroup.clearLayers();
  boundaryLayerGroup.clearLayers();
  if (marker) { map.removeLayer(marker); marker = null; }

  // Draw the full route line (thin, grey background)
  if (routeData.route_geometry && routeData.route_geometry.length > 0) {
    const routeCoords = routeData.route_geometry.map(c => [c[1], c[0]]);
    L.polyline(routeCoords, {
      color: '#94a3b8', weight: 3, opacity: 0.4
    }).addTo(routeLayerGroup);
  }

  // Draw colored zone segments
  const zones = routeData.zones || [];
  zones.forEach((zone) => {
    L.polyline(
      [[zone.from_lat, zone.from_lon], [zone.to_lat, zone.to_lon]],
      { color: zone.color || '#3b82f6', weight: 6, opacity: 0.8 }
    ).addTo(routeLayerGroup);

    const midLat = (zone.from_lat + zone.to_lat) / 2;
    const midLon = (zone.from_lon + zone.to_lon) / 2;

    const icon = L.divIcon({
      className: 'weather-zone-icon',
      html: `<div style="background:${zone.color};color:white;padding:4px 8px;border-radius:12px;font-size:11px;white-space:nowrap;box-shadow:0 2px 6px rgba(0,0,0,0.3);text-align:center;">${zone.weather_icon} ${zone.weather?.condition || ''}</div>`,
      iconSize: [0, 0],
      iconAnchor: [0, 0]
    });

    L.marker([midLat, midLon], { icon })
      .bindPopup(
        `<div style="min-width:180px">` +
        `<b>${zone.from_city} → ${zone.to_city}</b>` +
        `<hr style="margin:4px 0">` +
        `${zone.weather_icon} ${zone.weather?.condition || 'N/A'}<br>` +
        `🌡 ${zone.weather?.temperature ?? 'N/A'}°C<br>` +
        `💧 ${zone.weather?.precipitation ?? 0} mm<br>` +
        `💨 ${zone.weather?.wind_speed ?? 'N/A'} km/h<br>` +
        `🕐 Arrival: ${zone.arrival_time ? new Date(zone.arrival_time).toLocaleTimeString() : 'N/A'}<br>` +
        `📏 ${zone.distance_km?.toFixed(1) || '?'} km` +
        `</div>`
      )
      .addTo(routeLayerGroup);
  });

  // Origin marker (green A)
  if (routeData.origin) {
    L.marker([routeData.origin.latitude, routeData.origin.longitude], {
      icon: L.divIcon({
        className: 'route-endpoint',
        html: '<div style="background:#22c55e;color:white;padding:6px 10px;border-radius:50%;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3);text-align:center;">A</div>',
        iconSize: [30, 30], iconAnchor: [15, 15]
      })
    }).bindPopup(`<b>Start: ${routeData.origin.city}</b>`).addTo(routeLayerGroup);
  }

  // Destination marker (red B)
  if (routeData.destination) {
    L.marker([routeData.destination.latitude, routeData.destination.longitude], {
      icon: L.divIcon({
        className: 'route-endpoint',
        html: '<div style="background:#ef4444;color:white;padding:6px 10px;border-radius:50%;font-weight:bold;box-shadow:0 2px 6px rgba(0,0,0,0.3);text-align:center;">B</div>',
        iconSize: [30, 30], iconAnchor: [15, 15]
      })
    }).bindPopup(`<b>End: ${routeData.destination.city}</b>`).addTo(routeLayerGroup);
  }

  // Fit map to route
  if (routeData.route_geometry && routeData.route_geometry.length > 0) {
    const bounds = routeData.route_geometry.map(c => [c[1], c[0]]);
    map.fitBounds(bounds, { padding: [30, 30] });
  }
};


// =============================================
// NDVI: Display NDVI results on map
// =============================================

window.drawNDVI = function (ndviData) {
  ndviLayerGroup.clearLayers();

  if (!ndviData.grid || ndviData.grid.length === 0) return;

  ndviData.grid.forEach(point => {
    if (point.ndvi === null || point.category === 'no_data') return;
    L.circleMarker([point.lat, point.lon], {
      radius: 10,
      fillColor: point.color || '#d1d5db',
      fillOpacity: 0.75,
      color: '#fff',
      weight: 1
    }).bindPopup(
      `<b>NDVI: ${point.ndvi?.toFixed(3) || 'N/A'}</b><br>Health: ${point.category}`
    ).addTo(ndviLayerGroup);
  });

  const lats = ndviData.grid.filter(p => p.ndvi !== null).map(p => p.lat);
  const lons = ndviData.grid.filter(p => p.ndvi !== null).map(p => p.lon);
  if (lats.length > 0) {
    map.fitBounds(
      [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]],
      { padding: [30, 30] }
    );
  }
};


// =============================================
// UTILITIES
// =============================================

window.clearAllLayers = function () {
  routeLayerGroup.clearLayers();
  boundaryLayerGroup.clearLayers();
  ndviLayerGroup.clearLayers();
  drawnItems.clearLayers();
  if (marker) { map.removeLayer(marker); marker = null; }
};

// Expose for NDVI drawing
window.mapDrawnItems = drawnItems;
window.leafletMap = map;
