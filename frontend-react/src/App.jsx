import { useState, useRef, useEffect, useCallback } from "react";
import {
  Mic,
  MicOff,
  Send,
  CloudSun,
  AlertTriangle,
  Volume2,
  Sparkles,
  Navigation,
  Sprout,
  MessageSquare,
  Trash2,
  MousePointer2,
  Check,
} from "lucide-react";
import WeatherMap from "./components/WeatherMap";
import NDVIReport from "./components/NDVIReport";
import SatelliteCalendar from "./components/SatelliteCalendar";

const BACKEND_URL = "http://127.0.0.1:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");

  // Chat state
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "👋 Hello! Ask me about the weather in any city (e.g., 'Will it rain in Kochi tomorrow?').",
    },
  ]);
  const [input, setInput] = useState("");
  const [lang, setLang] = useState("en");
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [currentLocation, setCurrentLocation] = useState(null);
  const [alertMsg, setAlertMsg] = useState(null);

  // Route state
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [routePath, setRoutePath] = useState(null);
  const [routeWeather, setRouteWeather] = useState(null);
  const [routeError, setRouteError] = useState(null);

  // NDVI / Vegetation state
  const [drawnPolygon, setDrawnPolygon] = useState(null);
  const [drawingPoints, setDrawingPoints] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [polygonAreaHa, setPolygonAreaHa] = useState(null);

  // Satellite availability state
  const [availableDates, setAvailableDates] = useState([]);
  const [availabilityLoading, setAvailabilityLoading] = useState(false);
  const [selectedObservation, setSelectedObservation] = useState(null);

  // NDVI analysis state
  const [ndviLoading, setNdviLoading] = useState(false);
  const [ndviResult, setNdviResult] = useState(null);
  const [ndviError, setNdviError] = useState(null);

  const chatEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // =============================================
  // Speech
  // =============================================
  const speak = (text) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    const langMap = { en: "en-IN", hi: "hi-IN", ml: "ml-IN" };
    utterance.lang = langMap[lang] || "en-IN";
    utterance.rate = 1.0;
    window.speechSynthesis.speak(utterance);
  };

  // =============================================
  // Chat
  // =============================================
  const handleSend = async (queryText) => {
    const textToSend = queryText || input;
    if (!textToSend.trim() || loading) return;

    const userMessage = textToSend.trim();
    setMessages((prev) => [...prev, { sender: "user", text: userMessage }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(
        `${BACKEND_URL}/chat?question=${encodeURIComponent(userMessage)}&lang=${encodeURIComponent(lang)}`
      );
      const data = await res.json();
      const botReply = data.answer_text || data.message || "Could not retrieve weather details.";
      setMessages((prev) => [...prev, { sender: "bot", text: botReply }]);
      speak(botReply);
      if (data.location) setCurrentLocation(data.location);
      if (data.alert) setAlertMsg(data.alert);
    } catch {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Unable to connect to backend service. Is Uvicorn running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // =============================================
  // Route Weather
  // =============================================
  const handleRouteSearch = async (e) => {
    e.preventDefault();
    if (!origin.trim() || !destination.trim()) return;
    setLoading(true);
    setRouteError(null);
    setRouteWeather(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/route/weather?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}`
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not calculate the route.");
      const points = (data.route_geometry || []).map(([longitude, latitude]) => [latitude, longitude]);
      if (points.length < 2) throw new Error("The route service returned no map geometry.");
      setRoutePath(points);
      setRouteWeather(data);
      setCurrentLocation(data.origin);
    } catch (err) {
      setRouteError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // =============================================
  // Polygon Drawing (click-to-draw)
  // =============================================
  const calcArea = (coords) => {
    if (coords.length < 3) return 0;
    const R = 6378137;
    let area = 0;
    const n = coords.length;
    for (let i = 0; i < n; i++) {
      const [lat1, lon1] = coords[i];
      const [lat2, lon2] = coords[(i + 1) % n];
      const x1 = R * ((lon1 * Math.PI) / 180) * Math.cos((lat1 * Math.PI) / 180);
      const y1 = R * ((lat1 * Math.PI) / 180);
      const x2 = R * ((lon2 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180);
      const y2 = R * ((lat2 * Math.PI) / 180);
      area += x1 * y2 - x2 * y1;
    }
    return (Math.abs(area) / 2 / 10000).toFixed(2);
  };

  const handleStartDrawing = () => {
    setIsDrawing(true);
    setDrawingPoints([]);
    setDrawnPolygon(null);
    setPolygonAreaHa(null);
    setAvailableDates([]);
    setSelectedObservation(null);
    setNdviResult(null);
    setNdviError(null);
  };

  const handlePointAdded = useCallback((point) => {
    setDrawingPoints((prev) => [...prev, point]);
  }, []);

  const handleFinishDrawing = () => {
    if (drawingPoints.length >= 3) {
      setDrawnPolygon(drawingPoints);
      setPolygonAreaHa(calcArea(drawingPoints));
      // Auto-fetch satellite availability after polygon is drawn
      fetchAvailability(drawingPoints);
    }
    setIsDrawing(false);
    setDrawingPoints([]);
  };

  const handleClearNdvi = () => {
    setDrawnPolygon(null);
    setDrawingPoints([]);
    setIsDrawing(false);
    setPolygonAreaHa(null);
    setAvailableDates([]);
    setSelectedObservation(null);
    setNdviResult(null);
    setNdviError(null);
  };

  // =============================================
  // Satellite Availability
  // =============================================
  const fetchAvailability = async (polygon) => {
    setAvailabilityLoading(true);
    setAvailableDates([]);
    setSelectedObservation(null);
    try {
      const res = await fetch(`${BACKEND_URL}/ndvi/availability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ polygon }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch availability.");
      setAvailableDates(data.observations || []);
    } catch (err) {
      console.error("Availability fetch error:", err);
      setNdviError("Could not fetch satellite availability: " + err.message);
    } finally {
      setAvailabilityLoading(false);
    }
  };

  const handleDateSelected = (dateStr) => {
    setSelectedObservation(dateStr);
    setNdviResult(null);
    setNdviError(null);
  };

  // =============================================
  // NDVI Analysis
  // =============================================
  const handleNdviAnalyze = async () => {
    if (!drawnPolygon || drawnPolygon.length < 3 || !selectedObservation) return;
    setNdviLoading(true);
    setNdviError(null);
    setNdviResult(null);

    // Find the selected observation details
    const obs = availableDates.find((o) => o.date === selectedObservation);

    try {
      const res = await fetch(`${BACKEND_URL}/ndvi/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          polygon: drawnPolygon,
          date: selectedObservation,
          source: obs?.source || "auto",
          scene_id: obs?.scene_id || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "NDVI analysis failed.");
      setNdviResult(data);
    } catch (err) {
      setNdviError(err.message);
    } finally {
      setNdviLoading(false);
    }
  };

  // =============================================
  // Voice Recording
  // =============================================
  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.wav");
        try {
          const res = await fetch(`${BACKEND_URL}/speech-to-text`, { method: "POST", body: formData });
          const data = await res.json();
          if (data.transcript) handleSend(data.transcript);
        } catch (err) {
          console.error("Transcription error:", err);
        }
      };
      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch {
      alert("Microphone permission denied.");
    }
  };

  // =============================================
  // RENDER
  // =============================================
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-100 via-blue-50 to-indigo-100 flex items-center justify-center p-3">
      <div className="w-full max-w-lg bg-white/95 backdrop-blur-md rounded-3xl shadow-2xl border border-white/60 flex flex-col h-[92vh] overflow-hidden">

        {/* Header */}
        <header className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-white/60">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-500/10 text-blue-600 rounded-xl">
              <CloudSun className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-base font-bold text-slate-800 flex items-center gap-1">
                WeatherGPT
                <Sparkles className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
              </h1>
              <p className="text-[11px] text-slate-500">Agro-Travel &amp; Atmospheric Intelligence</p>
            </div>
          </div>
          <select
            value={lang}
            onChange={(e) => setLang(e.target.value)}
            className="text-xs font-semibold bg-slate-100 border border-slate-200 rounded-xl px-2.5 py-1.5 text-slate-700 outline-none hover:bg-slate-200 transition"
          >
            <option value="en">English</option>
            <option value="ml">Malayalam</option>
            <option value="hi">Hindi</option>
          </select>
        </header>

        {/* 3-Tab Selector */}
        <div className="flex border-b border-slate-100 bg-slate-50/70 p-1 gap-1">
          {[
            { key: "chat", icon: MessageSquare, label: "Chat", color: "blue" },
            { key: "route", icon: Navigation, label: "Route", color: "blue" },
            { key: "vegetation", icon: Sprout, label: "Vegetation", color: "emerald" },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-1.5 rounded-xl text-xs font-medium flex items-center justify-center gap-1.5 transition ${
                activeTab === tab.key
                  ? `bg-white text-${tab.color}-600 shadow-sm font-semibold`
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Alert Banner */}
        {alertMsg && (
          <div className="bg-amber-50 border-b border-amber-200/60 px-4 py-2 flex items-center gap-2 text-xs font-medium text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <span>{alertMsg}</span>
          </div>
        )}

        {/* =========== CHAT TAB =========== */}
        {activeTab === "chat" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.map((m, idx) => (
              <div key={idx} className={`flex items-start gap-2 ${m.sender === "user" ? "justify-end" : "justify-start"}`}>
                {m.sender === "bot" && (
                  <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-0.5 text-[11px] font-bold">AI</div>
                )}
                <div className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed shadow-sm ${
                  m.sender === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-slate-100 text-slate-800 rounded-bl-none border border-slate-200/60"
                }`}>
                  {m.text}
                </div>
                {m.sender === "bot" && (
                  <button onClick={() => speak(m.text)} className="text-slate-400 hover:text-slate-600 p-0.5">
                    <Volume2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            ))}
            {loading && <div className="text-xs text-slate-400 italic pl-8">Analyzing atmospheric conditions...</div>}
            <div ref={chatEndRef} />
          </div>
        )}

        {/* =========== ROUTE TAB =========== */}
        {activeTab === "route" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <form onSubmit={handleRouteSearch} className="space-y-2">
              <input type="text" value={origin} onChange={(e) => setOrigin(e.target.value)}
                placeholder="Start City (e.g., Kochi)"
                className="w-full bg-slate-100 border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-500" />
              <input type="text" value={destination} onChange={(e) => setDestination(e.target.value)}
                placeholder="Destination City (e.g., Munnar)"
                className="w-full bg-slate-100 border border-slate-200 rounded-xl px-3 py-2 text-xs outline-none focus:border-blue-500" />
              <button type="submit" disabled={loading}
                className="w-full py-2 bg-blue-600 text-white rounded-xl text-xs font-semibold hover:bg-blue-700 transition disabled:opacity-50">
                {loading ? "Calculating Route..." : "Analyze Route Forecast"}
              </button>
            </form>
            {routeWeather && (
              <div className="p-3 bg-blue-50/70 rounded-2xl border border-blue-100 text-xs space-y-2">
                <p className="font-semibold text-blue-900">Route Analysis Ready</p>
                <p className="text-slate-600">{routeWeather.total_distance_km?.toFixed(1)} km · {routeWeather.total_duration_hours?.toFixed(1)} hours</p>
                {routeWeather.summary?.warnings?.length > 0 && (
                  <div className="rounded-lg bg-amber-50 p-2 text-amber-800">
                    <p className="font-semibold">Weather warnings</p>
                    {routeWeather.summary.warnings.map((w) => <p key={w}>{w}</p>)}
                  </div>
                )}
                <p className="font-semibold text-blue-900">Point-to-point forecast</p>
                <div className="space-y-1.5">
                  {(routeWeather.route_points || []).map((point, index) => {
                    const weather = point.weather || {};
                    return (
                      <div key={`${point.lat}-${point.lon}-${index}`} className="rounded-lg bg-white/80 p-2 text-slate-600">
                        <div className="flex justify-between gap-2 font-semibold text-slate-800">
                          <span>{point.city_name || `Point ${index + 1}`}</span>
                          <span>{weather.condition || "No forecast"}</span>
                        </div>
                        <div>{weather.temperature ?? "-"} °C · {weather.precipitation ?? "-"} mm · {weather.wind_speed ?? "-"} km/h</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {routeError && <p className="text-xs text-rose-600">{routeError}</p>}
          </div>
        )}

        {/* =========== VEGETATION TAB =========== */}
        {activeTab === "vegetation" && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {/* Drawing Controls */}
            <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/60 space-y-2.5">
              <p className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
                <Sprout className="w-4 h-4" /> Vegetation Health Analysis
              </p>

              {/* Step 1: Draw polygon */}
              {!drawnPolygon && !isDrawing && (
                <div className="space-y-2">
                  <p className="text-xs text-slate-600">
                    Click <strong>"Start Drawing"</strong>, then click on the map to place polygon points (min 3). Click <strong>"Finish"</strong> when done.
                  </p>
                  <button onClick={handleStartDrawing}
                    className="w-full py-2 bg-emerald-600 text-white rounded-xl text-xs font-semibold hover:bg-emerald-700 transition flex items-center justify-center gap-1.5">
                    <MousePointer2 className="w-3.5 h-3.5" /> Start Drawing Polygon
                  </button>
                </div>
              )}

              {/* Step 2: Currently drawing */}
              {isDrawing && (
                <div className="space-y-2">
                  <p className="text-xs text-emerald-700 font-medium animate-pulse">
                    🖊️ Click on the map to add points ({drawingPoints.length} placed)
                  </p>
                  <div className="flex gap-2">
                    <button onClick={handleFinishDrawing} disabled={drawingPoints.length < 3}
                      className="flex-1 py-2 bg-emerald-600 text-white rounded-xl text-xs font-semibold hover:bg-emerald-700 transition disabled:opacity-40 flex items-center justify-center gap-1.5">
                      <Check className="w-3.5 h-3.5" /> Finish Polygon
                    </button>
                    <button onClick={handleClearNdvi}
                      className="p-2 bg-slate-100 text-slate-600 rounded-xl hover:bg-slate-200 transition border border-slate-200">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Polygon complete — show area + clear */}
              {drawnPolygon && (
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-600">✅ Polygon selected</span>
                    <span className="text-[10px] text-slate-400 ml-2">{drawnPolygon.length} vertices</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-emerald-700">{polygonAreaHa} ha</span>
                    <button onClick={handleClearNdvi}
                      className="p-1.5 bg-slate-100 text-slate-500 rounded-lg hover:bg-slate-200 transition border border-slate-200"
                      title="Clear polygon">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Step 4: Satellite Availability Calendar (auto-shows after polygon) */}
            {drawnPolygon && (
              <SatelliteCalendar
                observations={availableDates}
                selectedDate={selectedObservation}
                onDateSelected={handleDateSelected}
                loading={availabilityLoading}
              />
            )}

            {/* Step 5: Analyze button (only after a date is selected) */}
            {drawnPolygon && selectedObservation && !ndviResult && (
              <button onClick={handleNdviAnalyze} disabled={ndviLoading}
                className="w-full py-2.5 bg-emerald-600 text-white rounded-xl text-xs font-semibold hover:bg-emerald-700 transition disabled:opacity-40">
                {ndviLoading ? "🛰️ Fetching satellite data..." : "📊 Analyze Vegetation Health"}
              </button>
            )}

            {/* Error */}
            {ndviError && (
              <div className="p-3 rounded-xl border border-rose-200 bg-rose-50 text-xs text-rose-700">
                ❌ {ndviError}
              </div>
            )}

            {/* Loading */}
            {ndviLoading && (
              <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50 text-xs text-emerald-700 text-center animate-pulse">
                🛰️ Analyzing satellite data...<br />
                <span className="text-[10px] text-slate-500">This may take 20–60 seconds.</span>
              </div>
            )}

            {/* Step 6: Full NDVI Report */}
            <NDVIReport result={ndviResult} />
          </div>
        )}

        {/* =========== MAP (always visible) =========== */}
        <div className="p-3 pt-0">
          <WeatherMap
            location={currentLocation}
            routePath={routePath}
            ndviResult={ndviResult}
            routePoints={routeWeather?.route_points}
            drawnPolygon={drawnPolygon}
            drawingPoints={drawingPoints}
            isDrawing={isDrawing}
            onPointAdded={handlePointAdded}
          />
        </div>

        {/* =========== CHAT INPUT (only on chat tab) =========== */}
        {activeTab === "chat" && (
          <div className="p-3 border-t border-slate-100 bg-white/60">
            <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex items-center gap-2">
              <input type="text" value={input} onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about rain, temperature, or travel advice..."
                className="flex-1 bg-slate-100 border border-slate-200 rounded-2xl px-3.5 py-2 text-xs outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500" />
              <button type="button" onClick={toggleRecording}
                className={`p-2 rounded-xl transition ${isRecording ? "bg-rose-500 text-white animate-pulse" : "bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200"}`}>
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>
              <button type="submit" disabled={loading || !input.trim()}
                className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition disabled:opacity-50">
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}