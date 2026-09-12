// ============================================================
// map.js — Interactive Map for WeatherGPT
// Person 4 owns this file.
// ============================================================
//
// WHAT THIS FILE DOES:
//   1. Creates an interactive map in the <div id="map"> element
//      that Person 2 added to index.html
//   2. Shows OpenStreetMap tiles as the map background (free!)
//   3. Exposes window.updateMap() so chat.js can move the map
//      whenever the user searches for a city
//
// HOW IT CONNECTS TO THE REST OF THE APP:
//   chat.js (Person 2) calls:
//       window.updateMap(data.location)
//   where data.location looks like:
//       { city: "Delhi", country: "India", latitude: 28.65, longitude: 77.23 }
//
// LIBRARIES USED:
//   Leaflet.js — already loaded in index.html via a <script> tag:
//   <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
//   So "L" (the Leaflet object) is already available here.
// ============================================================


// --- STEP 1: Create the map ---
//
// L.map('map') creates a Leaflet map inside the HTML element with id="map"
// .setView([lat, lon], zoomLevel) sets the starting position
//
// We start at Kerala (lat=10.0, lon=76.3) because the project is Kerala-focused
// Zoom level 6 = country/state level view (1=whole world, 18=street level)
let map = L.map('map').setView([10.0, 76.3], 6);

// --- STEP 2: Add the map background (tiles) ---
//
// L.tileLayer() loads the background map images from OpenStreetMap's servers
// The URL template {s}.tile.openstreetmap.org/{z}/{x}/{y}.png is how Leaflet
// requests individual 256x256 tile images:
//   {s} = subdomain (a/b/c) for load balancing
//   {z} = zoom level
//   {x} = tile column
//   {y} = tile row
//
// attribution = the copyright text shown at the bottom-right of the map
// (required by OpenStreetMap's license — always give credit!)
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);  // .addTo(map) actually puts the tiles onto our map


// --- STEP 3: Track the map marker ---
//
// "marker" holds the current pin on the map.
// We start with null (no pin) because no city has been searched yet.
// When updateMap() is called, we remove the old marker and add a new one.
let marker = null;


// --- STEP 4: Define the updateMap function ---
//
// We attach this to "window" (the global JavaScript object) so that
// OTHER script files (specifically chat.js) can call it.
//
// If we just wrote "function updateMap(...)" it would only be visible
// inside this file. By writing "window.updateMap = function(...)"
// we make it globally accessible to all scripts on the page.
//
// The "location" parameter is the JSON object from the backend:
//   { city: "Delhi", country: "India", latitude: 28.65, longitude: 77.23 }
window.updateMap = function(location) {
    // Extract the latitude and longitude from the location object
    const lat = location.latitude;   // e.g. 28.65195
    const lon = location.longitude;  // e.g. 77.23149

    // Move the map's camera to the new city
    // setView([lat, lon], zoom) animates the map to center on these coordinates
    // Zoom 9 = city level (you can see the whole city and surroundings)
    map.setView([lat, lon], 9);

    // Remove the old marker (pin) if one already exists
    // This prevents pins from piling up when the user searches multiple cities
    if (marker) {
        map.removeLayer(marker);
    }

    // Add a new marker (pin) at the city's coordinates
    // L.marker([lat, lon]) creates the pin
    // .addTo(map) places it on the map
    // .bindPopup(text) attaches a popup bubble to the pin
    // .openPopup() makes the popup automatically appear when the pin is added
    marker = L.marker([lat, lon])
        .addTo(map)
        .bindPopup(`${location.city}, ${location.country || ""}`)
        .openPopup();
};
