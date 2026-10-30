import { useState } from "react";
import {
  Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { fetchAccuracy } from "../api";
import KpiCard from "../components/KpiCard";
import { useAsync } from "../useAsync";
import { CUTOFFS, fmt } from "../utils";

export default function AccuracyPage() {
  const [cutoff, setCutoff] = useState("09:00");
  const { data, error } = useAsync(() => fetchAccuracy(cutoff), [cutoff]);

  return (
    <section>
      <h2>How accurate were the forecasts in January?</h2>
      <p className="muted">
        Every delivery day in January 2026, using only forecasts available at the decision time.
      </p>

      <div className="controls">
        <label>
          Decision time, day before (UTC)
          <select value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
            {CUTOFFS.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </div>

      {error && <p className="error">{error}</p>}
      {!data && !error && <p className="muted">Loading...</p>}

      {data && (
        <>
          <div className="cards">
            <KpiCard label="Average error (MAE)" value={`${fmt(data.summary.mae_mw)} MW`}
              hint={`${data.summary.mae_pct_of_mean.toFixed(1)}% of average wind`} />
            <KpiCard label="Bias" value={`${data.summary.bias_mw >= 0 ? "+" : ""}${fmt(data.summary.bias_mw)} MW`}
              hint={data.summary.bias_mw >= 0 ? "Forecast runs too high" : "Forecast runs too low"} />
            <KpiCard label="Bad-day error (P90)" value={`${fmt(data.summary.p90_abs_error_mw)} MW`}
              hint="9 in 10 hours are better than this" />
            <KpiCard label="RMSE" value={`${fmt(data.summary.rmse_mw)} MW`} hint="Punishes big misses" />
          </div>

          <h3>Does deciding later help?</h3>
          <div className="chart">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.by_cutoff}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="cutoff" />
                <YAxis unit=" MW" width={90} tickFormatter={fmt} />
                <Tooltip formatter={(value) => fmt(Number(value))} />
                <Bar dataKey="mae_mw" name="Average error" fill="#4f46e5" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <h3>Error by forecast horizon</h3>
          <p className="muted small">Hours between forecast publication and the delivery hour.</p>
          <div className="chart">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.by_horizon}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="horizon_h" unit=" h" />
                <YAxis unit=" MW" width={90} tickFormatter={fmt} />
                <Tooltip formatter={(value) => fmt(Number(value))} />
                <Bar dataKey="mae_mw" name="Average error" fill="#6366f1" />
                <Bar dataKey="bias_mw" name="Bias" fill="#f59e0b" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <h3>Forecast vs actual</h3>
          <p className="muted small">Points below the line mean the forecast was too high.</p>
          <div className="chart">
            <ResponsiveContainer width="100%" height={380}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="forecast_mw" name="Forecast" unit=" MW"
                  domain={[0, 24000]} tickFormatter={fmt} />
                <YAxis type="number" dataKey="actual_mw" name="Actual" unit=" MW"
                  domain={[0, 24000]} width={90} tickFormatter={fmt} />
                <Tooltip formatter={(value) => fmt(Number(value))} />
                <ReferenceLine segment={[{ x: 0, y: 0 }, { x: 24000, y: 24000 }]} stroke="#9ca3af" strokeDasharray="4 4" />
                <Scatter data={data.points} fill="#4f46e5" fillOpacity={0.4} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="muted small">
            Error percentiles come from the same month they describe, so they are in-sample.
          </p>
        </>
      )}
    </section>
  );
}