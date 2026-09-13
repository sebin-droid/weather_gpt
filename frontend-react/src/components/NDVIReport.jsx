/**
 * NDVIReport.jsx — Vegetation Health Report Component
 *
 * Displays comprehensive NDVI analysis results:
 * - Satellite source, resolution, cloud info
 * - Requested date vs observation date (never silently substituted)
 * - Average, median, min, max NDVI
 * - Health distribution bars with percentages and area
 * - Overall condition badge
 * - Human-readable explanation
 */

const HEALTH_CONFIG = {
  healthy: { emoji: "🟢", label: "Healthy", color: "#22c55e", bg: "bg-green-50", text: "text-green-800", bar: "bg-green-500" },
  moderate: { emoji: "🟡", label: "Moderate", color: "#eab308", bg: "bg-yellow-50", text: "text-yellow-800", bar: "bg-yellow-500" },
  poor: { emoji: "🟠", label: "Poor", color: "#f97316", bg: "bg-orange-50", text: "text-orange-800", bar: "bg-orange-500" },
  very_poor: { emoji: "🔴", label: "Very Poor", color: "#ef4444", bg: "bg-red-50", text: "text-red-800", bar: "bg-red-500" },
  unknown: { emoji: "⚪", label: "Unknown", color: "#9ca3af", bg: "bg-slate-50", text: "text-slate-600", bar: "bg-slate-400" },
};

function formatDate(dateStr) {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

export default function NDVIReport({ result }) {
  if (!result) return null;

  const health = HEALTH_CONFIG[result.overall_health] || HEALTH_CONFIG.unknown;
  const hasData = result.average_ndvi !== null && result.average_ndvi !== undefined;
  const dateMatch = result.data_available_for_requested_date;

  return (
    <div className="space-y-3 text-xs">
      {/* Satellite & Date Info */}
      <div className="p-3 rounded-xl border border-slate-200 bg-white space-y-1.5">
        <p className="font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
          🛰️ Satellite Data
        </p>

        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          <div className="flex justify-between col-span-2">
            <span className="text-slate-500">Requested date:</span>
            <span className="font-medium text-slate-800">{formatDate(result.requested_date)}</span>
          </div>
          <div className="flex justify-between col-span-2">
            <span className="text-slate-500">Observation date:</span>
            <span className="font-medium text-slate-800">{formatDate(result.data_date) || "N/A"}</span>
          </div>
          <div className="flex justify-between col-span-2">
            <span className="text-slate-500">Source:</span>
            <span className="font-medium text-slate-800">{result.data_source || "Unknown"}</span>
          </div>
          {result.resolution && (
            <div className="flex justify-between col-span-2">
              <span className="text-slate-500">Resolution:</span>
              <span className="font-medium text-slate-800">{result.resolution}</span>
            </div>
          )}
        </div>

        {/* Date mismatch warning */}
        {result.data_date && !dateMatch && (
          <div className="mt-2 p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px]">
            ⚠️ Data for <strong>{formatDate(result.requested_date)}</strong> was not available.
            Analysis uses the nearest observation from <strong>{formatDate(result.data_date)}</strong>.
          </div>
        )}

        {/* Date match success */}
        {result.data_date && dateMatch && (
          <div className="mt-2 p-2 rounded-lg bg-green-50 border border-green-200 text-green-800 text-[11px]">
            ✅ Satellite data matched the requested date.
          </div>
        )}

        {/* No data at all */}
        {!result.data_date && !hasData && (
          <div className="mt-2 p-2 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-[11px]">
            ❌ No satellite observations available for this date. Please select a different date from the availability calendar above.
          </div>
        )}

        {/* Source note (MODIS fallback info) */}
        {result.source_note && (
          <div className="mt-1.5 p-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 text-[10px]">
            ℹ️ {result.source_note}
          </div>
        )}
      </div>

      {/* Health Summary Card */}
      {hasData && (
        <div className={`p-3 rounded-xl border ${health.bg} space-y-2`}>
          <div className="flex items-center justify-between">
            <p className="font-semibold text-slate-800">🌱 Vegetation Health</p>
            <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${health.text} ${health.bg} border`}>
              {health.emoji} {health.label}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-white/70 rounded-lg p-2">
              <p className="text-slate-500 text-[10px]">Average NDVI</p>
              <p className="font-bold text-slate-900 text-sm">{result.average_ndvi?.toFixed(3)}</p>
            </div>
            <div className="bg-white/70 rounded-lg p-2">
              <p className="text-slate-500 text-[10px]">Median NDVI</p>
              <p className="font-bold text-slate-900 text-sm">{result.median_ndvi?.toFixed(3)}</p>
            </div>
            <div className="bg-white/70 rounded-lg p-2">
              <p className="text-slate-500 text-[10px]">Min / Max</p>
              <p className="font-bold text-slate-900 text-sm">
                {result.min_ndvi?.toFixed(2)} — {result.max_ndvi?.toFixed(2)}
              </p>
            </div>
            <div className="bg-white/70 rounded-lg p-2">
              <p className="text-slate-500 text-[10px]">Selected Area</p>
              <p className="font-bold text-slate-900 text-sm">{result.area_hectares} ha</p>
              {result.area_sq_km && (
                <p className="text-[9px] text-slate-400">{result.area_sq_km} km²</p>
              )}
            </div>
          </div>

          {/* Data quality note */}
          <p className="text-[10px] text-slate-500">
            Based on {result.total_valid_points || result.valid_pixels || "?"} of{" "}
            {result.total_points || result.total_pixels || "?"} sample points with valid data
            {result.clear_percentage ? ` (${result.clear_percentage}% clear)` : ""}.
          </p>
        </div>
      )}

      {/* Health Distribution Bars */}
      {hasData && result.health_distribution && (
        <div className="p-3 rounded-xl border border-slate-200 bg-white space-y-2">
          <p className="font-semibold text-slate-700 text-[11px] uppercase tracking-wider">
            Vegetation Condition Classification
          </p>

          {["healthy", "moderate", "poor", "very_poor"].map((key) => {
            const dist = result.health_distribution[key];
            const cfg = HEALTH_CONFIG[key];
            if (!dist) return null;

            return (
              <div key={key} className="space-y-0.5">
                <div className="flex justify-between items-center">
                  <span className="text-slate-700 font-medium">
                    {cfg.emoji} {cfg.label}
                  </span>
                  <span className="text-slate-600">
                    {dist.percentage}% · {dist.area_hectares} ha
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${cfg.bar}`}
                    style={{ width: `${Math.max(dist.percentage, 1)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Explanation */}
      {result.explanation && (
        <div className="p-3 rounded-xl border border-blue-100 bg-blue-50/50 space-y-1">
          <p className="font-semibold text-blue-800 text-[11px]">ℹ️ Interpretation</p>
          <p className="text-slate-700 leading-relaxed">{result.explanation}</p>
        </div>
      )}

      {/* NDVI Scale Legend */}
      <div className="p-3 rounded-xl border border-slate-200 bg-white">
        <p className="font-semibold text-slate-700 text-[11px] uppercase tracking-wider mb-1.5">
          NDVI Scale
        </p>
        <div className="grid grid-cols-4 gap-1 text-[10px] text-center">
          {[
            { range: "0.6–1.0", label: "Healthy", color: "#22c55e" },
            { range: "0.4–0.6", label: "Moderate", color: "#eab308" },
            { range: "0.2–0.4", label: "Poor", color: "#f97316" },
            { range: "<0.2", label: "Very Poor", color: "#ef4444" },
          ].map((item) => (
            <div key={item.label} className="flex flex-col items-center gap-0.5">
              <div className="w-4 h-4 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="font-medium text-slate-700">{item.label}</span>
              <span className="text-slate-400">{item.range}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
