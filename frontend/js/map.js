let map = L.map('map').setView([10.0, 76.3], 6); // default view: Kerala
let marker = null;

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

// This function is called from chat.js whenever a location is found
window.updateMap = function (location) {
  const lat = location.latitude;
  const lon = location.longitude;

  map.setView([lat, lon], 9);

  if (marker) {
    map.removeLayer(marker);
  }
  marker = L.marker([lat, lon]).addTo(map)
    .bindPopup(`${location.city}, ${location.country || ""}`)
    .openPopup();
};
