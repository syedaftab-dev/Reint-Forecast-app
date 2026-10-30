import { useState } from "react";
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { fetchForecast } from "../api";
import KpiCard from "../components/KpiCard";
import { useAsync } from "../useAsync";
import { CUTOFFS, fmt } from "../utils";

export default function ForecastPage() {
  const [date, setDate] = useState("2026-01-15");
  const [cutoff, setCutoff] = useState("09:00");
  const { data, error } = useAsync(() => fetchForecast(date, cutoff), [date, cutoff]);

  const chartData = data?.rows.map((row) => ({
    hour: row.startTime.slice(11, 16),
    forecast: row.forecast_mw,
    actual: row.actual_mw,
    low: row.low_mw,
    band: row.high_mw - row.low_mw,
  }));

  // Energy the buyer should cover with backup power if wind lands at the low end of the band.
  const backupMwh = data?.rows.reduce((sum, row) => sum + row.forecast_mw - row.low_mw, 0) ?? 0;
  const published = data?.publish_times.map((t) => t.replace("T", " ").slice(0, 16)).join(", ");
  const overPct = data
    ? (data.summary.total_forecast_mwh / data.summary.total_actual_mwh - 1) * 100
    : 0;

  return (
    <section>
      <h2>Wind forecast for your delivery day</h2>
      <p className="muted">
        Shows the newest forecast published before your decision time on the day before delivery.
      </p>

      <div className="controls">
        <label>
          Delivery day
          <input type="date" min="2026-01-01" max="2026-01-31" value={date}
            onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          Decision time, day before (UTC)
          <select value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
            {CUTOFFS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading...</p>}

      {data && chartData && (
        <>
          <div className="cards">
            <KpiCard label="Forecast used" value={published ?? ""} hint="UTC publish time" />
            <KpiCard label="Forecast energy" value={`${fmt(data.summary.total_forecast_mwh)} MWh`}
              hint={`Peak ${fmt(data.summary.peak_forecast_mw)} MW`} />
            <KpiCard label="Backup for low-wind case" value={`${fmt(backupMwh)} MWh`}
              hint="Covers the low end of the range" />
            <KpiCard label="Actual wind" value={`${fmt(data.summary.total_actual_mwh)} MWh`}
              hint={`Forecast was ${overPct.toFixed(0)}% ${overPct >= 0 ? "above" : "below"} actual`} />
          </div>

          <div className="chart">
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis unit=" MW" width={90} tickFormatter={fmt} />
                <Tooltip formatter={(value) => fmt(Number(value))} />
                <Legend />
                <Area dataKey="low" stackId="range" stroke="none" fill="none" legendType="none" />
                <Area dataKey="band" stackId="range" name="Likely range" stroke="none"
                  fill="#c7d2fe" fillOpacity={0.7} />
                <Line dataKey="forecast" name="Forecast" stroke="#4f46e5" strokeWidth={2} dot={false} />
                <Line dataKey="actual" name="Actual" stroke="#059669" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <p className="muted small">
            Likely range uses the 10th and 90th percentile of forecast error across all of January,
            so it is an in-sample estimate. Times are UTC, hourly.
          </p>
        </>
      )}
    </section>
  );
}