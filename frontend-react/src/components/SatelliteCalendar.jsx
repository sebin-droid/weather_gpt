/**
 * SatelliteCalendar.jsx — Satellite Observation Availability Calendar
 *
 * Shows a compact month-view calendar with colored indicators for
 * satellite observation availability. Users click available dates
 * to select them for NDVI analysis.
 *
 * 🟢 Good (<30% cloud)
 * 🟡 Limited (30-60% cloud)
 * 🔴 Poor (>60% cloud)
 * 🔵 MODIS composite (16-day, 250m)
 * ⚪ No observation
 */

import { useState, useMemo } from "react";
import { ChevronLeft, ChevronRight, Satellite } from "lucide-react";

const QUALITY_STYLES = {
  good: {
    dot: "bg-green-500",
    ring: "ring-green-400",
    label: "Good",
    emoji: "🟢",
    textColor: "text-green-700",
  },
  limited: {
    dot: "bg-yellow-500",
    ring: "ring-yellow-400",
    label: "Limited",
    emoji: "🟡",
    textColor: "text-yellow-700",
  },
  poor: {
    dot: "bg-red-500",
    ring: "ring-red-400",
    label: "Poor",
    emoji: "🔴",
    textColor: "text-red-700",
  },
  composite: {
    dot: "bg-blue-500",
    ring: "ring-blue-400",
    label: "MODIS",
    emoji: "🔵",
    textColor: "text-blue-700",
  },
  unknown: {
    dot: "bg-gray-400",
    ring: "ring-gray-300",
    label: "Unknown",
    emoji: "⚪",
    textColor: "text-gray-500",
  },
};

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function SatelliteCalendar({
  observations,
  selectedDate,
  onDateSelected,
  loading,
}) {
  const [viewDate, setViewDate] = useState(() => new Date());

  // Build a map of date -> best observation
  const dateMap = useMemo(() => {
    const map = {};
    if (!observations) return map;

    for (const obs of observations) {
      const existing = map[obs.date];
      if (!existing) {
        map[obs.date] = obs;
      } else {
        // Prefer sentinel over modis, then lower cloud
        if (obs.source === "sentinel-2" && existing.source === "modis") {
          map[obs.date] = obs;
        } else if (
          obs.source === existing.source &&
          obs.cloud_cover_pct !== null &&
          (existing.cloud_cover_pct === null ||
            obs.cloud_cover_pct < existing.cloud_cover_pct)
        ) {
          map[obs.date] = obs;
        }
      }
    }
    return map;
  }, [observations]);

  // Calendar grid for current month
  const calendarDays = useMemo(() => {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // Monday = 0 in our grid
    let startDow = firstDay.getDay() - 1;
    if (startDow < 0) startDow = 6;

    const days = [];

    // Padding before month starts
    for (let i = 0; i < startDow; i++) {
      days.push({ day: null, date: null });
    }

    // Actual days
    for (let d = 1; d <= lastDay.getDate(); d++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({ day: d, date: dateStr });
    }

    return days;
  }, [viewDate]);

  const monthLabel = viewDate.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  const prevMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
  };

  // Selected observation details
  const selectedObs = selectedDate ? dateMap[selectedDate] : null;

  if (loading) {
    return (
      <div className="p-3 rounded-xl border border-blue-200 bg-blue-50/60 text-center">
        <p className="text-xs text-blue-700 animate-pulse flex items-center justify-center gap-1.5">
          <Satellite className="w-3.5 h-3.5" />
          Searching satellite observations...
        </p>
        <p className="text-[10px] text-slate-500 mt-1">
          Checking Sentinel-2 and MODIS archives
        </p>
      </div>
    );
  }

  if (!observations || observations.length === 0) {
    return (
      <div className="p-3 rounded-xl border border-slate-200 bg-slate-50 text-center">
        <p className="text-xs text-slate-600">
          No satellite observations found for this area.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="px-3 py-2 bg-slate-50 border-b border-slate-100">
        <p className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <Satellite className="w-3.5 h-3.5" />
          Satellite Observations
        </p>
      </div>

      {/* Month navigation */}
      <div className="flex items-center justify-between px-3 py-1.5">
        <button
          onClick={prevMonth}
          className="p-1 rounded-lg hover:bg-slate-100 transition text-slate-500"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="text-xs font-semibold text-slate-800">{monthLabel}</span>
        <button
          onClick={nextMonth}
          className="p-1 rounded-lg hover:bg-slate-100 transition text-slate-500"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Day headers */}
      <div className="grid grid-cols-7 px-2">
        {DAYS.map((d) => (
          <div
            key={d}
            className="text-center text-[9px] font-medium text-slate-400 py-0.5"
          >
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 px-2 pb-2 gap-y-0.5">
        {calendarDays.map((cell, idx) => {
          if (!cell.date) {
            return <div key={`empty-${idx}`} className="h-7" />;
          }

          const obs = dateMap[cell.date];
          const isSelected = selectedDate === cell.date;
          const today = new Date().toISOString().split("T")[0];
          const isToday = cell.date === today;
          const isFuture = cell.date > today;

          const style = obs ? QUALITY_STYLES[obs.quality] || QUALITY_STYLES.unknown : null;

          return (
            <button
              key={cell.date}
              onClick={() => obs && onDateSelected(cell.date)}
              disabled={!obs || isFuture}
              className={`h-7 rounded-lg text-[10px] font-medium relative flex flex-col items-center justify-center transition
                ${isSelected ? `ring-2 ${style?.ring || "ring-blue-400"} bg-blue-50 font-bold` : ""}
                ${obs && !isFuture ? "cursor-pointer hover:bg-slate-50" : "cursor-default"}
                ${isToday ? "border border-slate-300" : ""}
                ${isFuture ? "text-slate-300" : obs ? "text-slate-800" : "text-slate-400"}
              `}
              title={
                obs
                  ? `${obs.source === "sentinel-2" ? obs.satellite : "MODIS"} — ${obs.cloud_cover_pct !== null ? obs.cloud_cover_pct + "% cloud" : "composite"} — ${style?.label}`
                  : "No observation"
              }
            >
              <span>{cell.day}</span>
              {obs && !isFuture && (
                <div
                  className={`w-1.5 h-1.5 rounded-full ${style?.dot || "bg-gray-300"} absolute bottom-0.5`}
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Legend */}
      <div className="px-3 py-1.5 border-t border-slate-100 flex flex-wrap gap-x-3 gap-y-0.5">
        {[
          { ...QUALITY_STYLES.good, desc: "<30% cloud" },
          { ...QUALITY_STYLES.limited, desc: "30-60%" },
          { ...QUALITY_STYLES.poor, desc: ">60%" },
          { ...QUALITY_STYLES.composite, desc: "MODIS 16-day" },
        ].map((item) => (
          <div key={item.label} className="flex items-center gap-1 text-[9px] text-slate-500">
            <div className={`w-2 h-2 rounded-full ${item.dot}`} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Selected observation details */}
      {selectedObs && (
        <div className="px-3 py-2 border-t border-slate-100 bg-blue-50/40 space-y-0.5">
          <p className="text-[11px] font-semibold text-slate-700">
            Selected: {new Date(selectedObs.date + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })}
          </p>
          <div className="flex flex-wrap gap-x-3 text-[10px] text-slate-600">
            <span>
              🛰️ {selectedObs.source === "sentinel-2" ? selectedObs.satellite : "MODIS Terra"}
            </span>
            <span>
              📐 {selectedObs.resolution}
            </span>
            {selectedObs.cloud_cover_pct !== null && (
              <span>
                ☁️ {selectedObs.cloud_cover_pct}% cloud
              </span>
            )}
            <span className={QUALITY_STYLES[selectedObs.quality]?.textColor || ""}>
              {QUALITY_STYLES[selectedObs.quality]?.emoji}{" "}
              {QUALITY_STYLES[selectedObs.quality]?.label}
            </span>
          </div>
          {selectedObs.quality === "poor" && (
            <p className="text-[10px] text-amber-700 mt-1">
              ⚠️ High cloud cover — results may be limited.
            </p>
          )}
          {selectedObs.source === "modis" && (
            <p className="text-[10px] text-blue-600 mt-1">
              ℹ️ MODIS: 250m resolution, 16-day composite. Sentinel-2 (10m) coming soon.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
