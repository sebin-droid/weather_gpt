/**
 * WeatherMap.jsx — Interactive Map with Polygon Drawing & NDVI Visualization
 *
 * Features:
 * - Base map with street and satellite views
 * - Location markers from chat
 * - Route polyline with weather points
 * - Manual polygon drawing (simple click-to-draw, no external draw plugin)
 * - NDVI grid visualization clipped to user's polygon
 * - NDVI color legend
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Popup,
  Polyline,
  CircleMarker,
  Polygon as LeafletPolygon,
  LayersControl,
  useMap,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix default marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});


// =============================================
// Map auto-recenter component
// =============================================
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


// =============================================
// Click-to-draw polygon (no external plugin needed)
// =============================================
function ClickDrawHandler({ isDrawing, onPointAdded }) {
  useMapEvents({
    click(e) {
      if (isDrawing) {
        onPointAdded([e.latlng.lat, e.latlng.lng]);
      }
    },
  });
  return null;
}


// =============================================
// NDVI Legend Control
// =============================================
function NDVILegend({ visible }) {
  const map = useMap();
  const legendRef = useRef(null);

  useEffect(() => {
    if (!map) return;

    if (visible && !legendRef.current) {
      const legend = L.control({ position: "bottomright" });

      legend.onAdd = () => {
        const div = L.DomUtil.create("div", "ndvi-legend");
        div.style.cssText =
          "background:white;padding:8px 12px;border-radius:8px;font-size:11px;line-height:1.6;box-shadow:0 2px 8px rgba(0,0,0,0.15);border:1px solid #e2e8f0;";
        div.innerHTML = `
          <div style="font-weight:700;margin-bottom:4px;color:#334155;">Vegetation Health</div>
          <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#22c55e;margin-right:6px;vertical-align:middle;"></span>Healthy (&gt;0.6)</div>
          <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#eab308;margin-right:6px;vertical-align:middle;"></span>Moderate (0.4–0.6)</div>
          <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#f97316;margin-right:6px;vertical-align:middle;"></span>Poor (0.2–0.4)</div>
          <div><span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:#ef4444;margin-right:6px;vertical-align:middle;"></span>Very Poor (&lt;0.2)</div>
        `;
        return div;
      };

      legend.addTo(map);
      legendRef.current = legend;
    } else if (!visible && legendRef.current) {
      map.removeControl(legendRef.current);
      legendRef.current = null;
    }

    return () => {
      if (legendRef.current) {
        try { map.removeControl(legendRef.current); } catch(e) {}
        legendRef.current = null;
      }
    };
  }, [visible, map]);

  return null;
}


// =============================================
// Main WeatherMap Component
// =============================================
export default function WeatherMap({
  location,
  routePath,
  ndviResult,
  routePoints,
  drawnPolygon,
  drawingPoints,
  isDrawing,
  onPointAdded,
}) {
  const defaultPos = [9.9312, 76.2673]; // Kochi default
  const position = location
    ? [location.latitude, location.longitude]
    : defaultPos;

  const showNdviGrid = ndviResult?.grid?.length > 0;

  return (
    <div className="h-72 w-full rounded-2xl overflow-hidden shadow-inner border border-slate-200 relative">
      <MapContainer
        center={position}
        zoom={8}
        scrollWheelZoom={true}
        className="h-full w-full"
      >
        <LayersControl position="topright">
          <LayersControl.BaseLayer checked name="Street Map">
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
        </LayersControl>

        {/* Location Pin from chat */}
        {location && (
          <Marker position={position}>
            <Popup>
              <div className="font-sans text-xs">
                <strong>{location.city}</strong>
                <br />
                Lat: {location.latitude.toFixed(2)}, Lon:{" "}
                {location.longitude.toFixed(2)}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Route Polyline */}
        {routePath && routePath.length > 0 && (
          <Polyline
            positions={routePath}
            pathOptions={{
              color: "#2563eb",
              weight: 5,
              opacity: 0.85,
              dashArray: "8, 6",
            }}
          />
        )}

        {/* Route Weather Points */}
        {routePoints?.map((point, index) => (
          <CircleMarker
            key={`route-${point.lat}-${point.lon}-${index}`}
            center={[point.lat, point.lon]}
            radius={6}
            pathOptions={{
              color: point.weather?.condition?.toLowerCase().includes("rain")
                ? "#2563eb"
                : "#f59e0b",
              fillColor: point.weather?.condition?.toLowerCase().includes("rain")
                ? "#60a5fa"
                : "#fbbf24",
              fillOpacity: 0.9,
              weight: 2,
            }}
          >
            <Popup>
              <strong>{point.city_name || `Route point ${index + 1}`}</strong>
              <br />
              {point.weather?.condition || "No forecast"}
              <br />
              Temp: {point.weather?.temperature ?? "-"} °C
              <br />
              Rain: {point.weather?.precipitation ?? "-"} mm
            </Popup>
          </CircleMarker>
        ))}

        {/* Drawing points (while actively drawing) */}
        {drawingPoints && drawingPoints.length > 0 && (
          <>
            {/* Show the in-progress polygon outline */}
            <Polyline
              positions={[...drawingPoints, drawingPoints[0]]}
              pathOptions={{
                color: "#22c55e",
                weight: 2,
                dashArray: "6, 4",
                fillOpacity: 0,
              }}
            />
            {/* Show markers at each clicked point */}
            {drawingPoints.map((pt, i) => (
              <CircleMarker
                key={`draw-pt-${i}`}
                center={pt}
                radius={5}
                pathOptions={{
                  color: "#fff",
                  weight: 2,
                  fillColor: "#22c55e",
                  fillOpacity: 1,
                }}
              />
            ))}
          </>
        )}

        {/* Completed polygon outline */}
        {drawnPolygon && drawnPolygon.length >= 3 && (
          <LeafletPolygon
            positions={drawnPolygon.map((p) => [p[0], p[1]])}
            pathOptions={{
              color: "#22c55e",
              weight: 3,
              fillColor: "#22c55e",
              fillOpacity: 0.08,
            }}
          />
        )}

        {/* NDVI Grid — colored circles ONLY inside the user's polygon */}
        {showNdviGrid &&
          ndviResult.grid.map((point, index) => {
            if (point.ndvi === null || point.category === "no_data") return null;
            return (
              <CircleMarker
                key={`ndvi-${point.lat}-${point.lon}-${index}`}
                center={[point.lat, point.lon]}
                radius={10}
                pathOptions={{
                  color: "#fff",
                  weight: 1,
                  fillColor: point.color || "#d1d5db",
                  fillOpacity: 0.8,
                }}
              >
                <Popup>
                  <div style={{ minWidth: "120px" }}>
                    <strong>NDVI: {point.ndvi?.toFixed(3) ?? "N/A"}</strong>
                    <br />
                    Condition: {point.category?.replace("_", " ")}
                    <br />
                    Lat: {point.lat.toFixed(3)}°, Lon: {point.lon.toFixed(3)}°
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

        {/* Click handler for drawing */}
        <ClickDrawHandler isDrawing={isDrawing} onPointAdded={onPointAdded} />

        {/* NDVI Legend (shown after analysis) */}
        <NDVILegend visible={showNdviGrid} />

        <MapRecenter coords={location} routeCoords={routePath} />
      </MapContainer>
    </div>
  );
}