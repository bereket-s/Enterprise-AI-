"use client";

import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton, StatTile } from "@/components/ui";

const CANONICAL_FIELDS = ["product_id", "product_name", "quantity", "unit_price", "transaction_date", "customer_ref", "country"];

interface KPISummary {
  total_revenue: number;
  avg_daily_revenue: number;
  trend_pct: number;
  days_of_history: number;
  top_products: { sku: string; name: string; revenue: number }[];
}

interface ForecastOut {
  model_name: string;
  horizon_days: number;
  mae: number;
  rmse: number;
  mape: number;
  forecast_points: { date: string; actual?: number; predicted: number }[];
}

export default function BIPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; suggested_mapping: Record<string, string | null> } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [kpis, setKpis] = useState<KPISummary | null>(null);
  const [forecast, setForecast] = useState<ForecastOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadKpis = async () => {
    try {
      const resp = await api.get<KPISummary>("/api/bi/kpis");
      setKpis(resp.data);
    } catch {
      /* no data ingested yet */
    }
  };

  const loadForecast = async () => {
    try {
      const resp = await api.get<ForecastOut>("/api/bi/forecast/latest");
      setForecast(resp.data);
    } catch {
      /* not run yet */
    }
  };

  useEffect(() => {
    loadKpis();
    loadForecast();
  }, []);

  const onFileSelected = async (f: File) => {
    setFile(f);
    setError(null);
    const form = new FormData();
    form.append("file", f);
    try {
      const resp = await api.post("/api/bi/ingest/preview", form);
      setPreview(resp.data);
      const initial: Record<string, string> = {};
      CANONICAL_FIELDS.forEach((field) => {
        if (resp.data.suggested_mapping[field]) initial[field] = resp.data.suggested_mapping[field];
      });
      setMapping(initial);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  const commitIngest = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mapping", JSON.stringify(mapping));
      await api.post("/api/bi/ingest/commit", form);
      setPreview(null);
      setFile(null);
      await loadKpis();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const runForecast = async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.post<ForecastOut>("/api/bi/forecast/run");
      setForecast(resp.data);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Business Intelligence & Forecasting</h1>
          <p className="text-slate-500 text-sm mt-1">Sales KPIs, trend analysis and demand forecasting.</p>
        </div>
        <label className="rounded-md border border-brand-600 text-brand-700 px-4 py-2 text-sm font-medium cursor-pointer hover:bg-brand-50">
          Upload sales CSV
          <input type="file" accept=".csv" hidden onChange={(e) => e.target.files && onFileSelected(e.target.files[0])} />
        </label>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {preview && (
        <Card title="Confirm column mapping">
          <p className="text-sm text-slate-500 mb-4">
            We matched your file&apos;s columns automatically — adjust anything that looks wrong before importing.
          </p>
          <div className="grid grid-cols-2 gap-4 mb-4">
            {CANONICAL_FIELDS.map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{field}</label>
                <select
                  value={mapping[field] ?? ""}
                  onChange={(e) => setMapping((m) => ({ ...m, [field]: e.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">— not mapped —</option>
                  {preview.columns.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <PrimaryButton onClick={commitIngest} disabled={busy}>
            {busy ? "Importing..." : "Import data"}
          </PrimaryButton>
        </Card>
      )}

      {kpis && kpis.days_of_history > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <StatTile label="Total revenue" value={`$${kpis.total_revenue.toLocaleString()}`} sublabel={`${kpis.days_of_history} days of history`} />
            <StatTile label="Avg. daily revenue" value={`$${kpis.avg_daily_revenue.toLocaleString()}`} />
            <StatTile label="Trend" value={`${kpis.trend_pct >= 0 ? "+" : ""}${kpis.trend_pct}%`} sublabel="first half vs. second half" />
          </div>

          <Card title="Top products by revenue">
            <ul className="divide-y divide-slate-100">
              {kpis.top_products.map((p) => (
                <li key={p.sku} className="py-2 flex justify-between text-sm">
                  <span>{p.name}</span>
                  <span className="font-medium">${p.revenue.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Revenue forecast">
            {!forecast ? (
              <PrimaryButton onClick={runForecast} disabled={busy}>
                {busy ? "Training model..." : "Run forecast"}
              </PrimaryButton>
            ) : (
              <>
                <div className="flex gap-6 text-sm text-slate-500 mb-4">
                  <span>Model: {forecast.model_name}</span>
                  <span>MAE: {forecast.mae}</span>
                  <span>RMSE: {forecast.rmse}</span>
                  <span>MAPE: {forecast.mape}%</span>
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={forecast.forecast_points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="actual" stroke="#64748b" dot={false} name="Actual" />
                    <Line type="monotone" dataKey="predicted" stroke="#4f46e5" dot={false} name="Predicted" />
                  </LineChart>
                </ResponsiveContainer>
                <PrimaryButton onClick={runForecast} disabled={busy} className="mt-3">
                  {busy ? "Re-training..." : "Re-run forecast"}
                </PrimaryButton>
              </>
            )}
          </Card>
        </>
      ) : (
        <Card>
          <p className="text-sm text-slate-500">No sales data yet. Upload a CSV to get started.</p>
        </Card>
      )}
    </div>
  );
}
