// map.js — Interactive Map for WeatherGPT (Person 4)
// Uses Leaflet.js (loaded via CDN in index.html)

// Create the map centered on Kerala (default view)
let map = L.map('map').setView([10.0, 76.3], 6);

// Add OpenStreetMap tiles
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// Track the current marker so we can remove it when a new city is searched
let marker = null;

// Called from chat.js whenever a location is found
// location = { city, country, latitude, longitude }
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
};
