import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  LayersControl,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function MapRecenter({ coords, routeCoords }) {
  const map = useMap();
  useEffect(() => {
    if (routeCoords && routeCoords.length > 0) {
      const bounds = L.latLngBounds(routeCoords);
      map.fitBounds(bounds, { padding: [30, 30] });
    } else if (coords) {
      map.flyTo([coords.latitude, coords.longitude], 10, { duration: 1.2 });
    }
  }, [coords, routeCoords, map]);
  return null;
}

export default function WeatherMap({ location, routePath, showNdvi, ndviResult, routePoints }) {
  const defaultPos = [9.9312, 76.2673]; // Kochi default
  const position = location
    ? [location.latitude, location.longitude]
    : defaultPos;

  return (
    <div className="h-72 w-full rounded-2xl overflow-hidden shadow-inner border border-slate-200 relative">
      <MapContainer
        center={position}
        zoom={8}
        scrollWheelZoom={false}
        className="h-full w-full"
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Standard Street">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="Satellite View">
            <TileLayer
              attribution="Tiles &copy; Esri"
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            />
          </LayersControl.BaseLayer>

          {/* Vegetation / NDVI Layer */}
          {showNdvi && (
            <LayersControl.Overlay checked name="Vegetation Index (NDVI)">
              <TileLayer
                opacity={0.65}
                attribution="NASA GIBS / MODIS NDVI"
                url="https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png"
              />
            </LayersControl.Overlay>
          )}
        </LayersControl>

        {/* Location Pin */}
        {location && (
          <Marker position={position}>
            <Popup>
              <div className="font-sans text-xs">
                <strong>{location.city}</strong>
                <br />
                Lat: {location.latitude.toFixed(2)}, Lon: {location.longitude.toFixed(2)}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Dynamic Route Polyline */}
        {routePath && routePath.length > 0 && (
          <Polyline
            positions={routePath}
            pathOptions={{ color: "#2563eb", weight: 5, opacity: 0.85, dashArray: "8, 6" }}
          />
        )}

        {routePoints?.map((point, index) => (
          <CircleMarker
            key={`route-weather-${point.lat}-${point.lon}-${index}`}
            center={[point.lat, point.lon]}
            radius={6}
            pathOptions={{
              color: point.weather?.condition?.toLowerCase().includes("rain") ? "#2563eb" : "#f59e0b",
              fillColor: point.weather?.condition?.toLowerCase().includes("rain") ? "#60a5fa" : "#fbbf24",
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{point.city_name || `Route point ${index + 1}`}</strong>
              <br />
              {point.weather?.condition || "No forecast"}
              <br />
              Temperature: {point.weather?.temperature ?? "-"} C
              <br />
              Rain: {point.weather?.precipitation ?? "-"} mm
              <br />
              Arrival: {point.arrival_time ? new Date(point.arrival_time).toLocaleTimeString() : "-"}
            </Popup>
          </CircleMarker>
        ))}

        {ndviResult?.grid?.map((point) => (
          <CircleMarker
            key={`${point.lat}-${point.lon}`}
            center={[point.lat, point.lon]}
            radius={7}
            pathOptions={{
              color: point.color || "#94a3b8",
              fillColor: point.color || "#94a3b8",
              fillOpacity: 0.75,
              weight: 1,
            }}
          >
            <Popup>
              NDVI: {point.ndvi ?? "No data"}
              <br />
              Health: {point.category}
            </Popup>
          </CircleMarker>
        ))}

        <MapRecenter coords={location} routeCoords={routePath} />
      </MapContainer>
    </div>
  );
}