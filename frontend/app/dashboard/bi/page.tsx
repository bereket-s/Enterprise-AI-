"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { BarChart3, LineChart as LineChartIcon, PlayCircle, TrendingUp } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card, EmptyState, PageHeader, SkeletonStatRow, StatTile } from "@/components/ui";
import { CsvUploadCard } from "@/components/CsvUploadCard";

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
  const [kpis, setKpis] = useState<KPISummary | null>(null);
  const [forecast, setForecast] = useState<ForecastOut | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
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
    Promise.all([loadKpis(), loadForecast()]).finally(() => setLoadingInitial(false));
  }, []);

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
      <PageHeader
        icon={LineChartIcon}
        title="Business Intelligence & Forecasting"
        subtitle="Sales KPIs, trend analysis and demand forecasting."
      />

      {error && <Alert tone="error">{error}</Alert>}

      <CsvUploadCard module="bi" onImported={loadKpis} />

      {loadingInitial ? (
        <SkeletonStatRow />
      ) : kpis && kpis.days_of_history > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <StatTile
              icon={BarChart3}
              label="Total revenue"
              value={`$${kpis.total_revenue.toLocaleString()}`}
              sublabel={`${kpis.days_of_history} days of history`}
            />
            <StatTile icon={TrendingUp} label="Avg. daily revenue" value={`$${kpis.avg_daily_revenue.toLocaleString()}`} />
            <StatTile label="Trend" value={`${kpis.trend_pct >= 0 ? "+" : ""}${kpis.trend_pct}%`} trend={kpis.trend_pct} sublabel="first half vs. second half" />
          </div>

          <Card title="Top products by revenue">
            <ul className="divide-y divide-slate-100">
              {kpis.top_products.map((p, i) => (
                <li key={p.sku} className="py-2.5 flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2.5">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-[10px] font-semibold text-slate-500">
                      {i + 1}
                    </span>
                    {p.name}
                  </span>
                  <span className="font-medium">${p.revenue.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Revenue forecast">
            {!forecast ? (
              <EmptyState
                icon={LineChartIcon}
                title="No forecast yet"
                description="Train a forecasting model on your ingested sales history to see predicted revenue."
                action={
                  <Button icon={PlayCircle} onClick={runForecast} loading={busy}>
                    {busy ? "Training model..." : "Run forecast"}
                  </Button>
                }
              />
            ) : (
              <>
                <div className="flex flex-wrap gap-2 mb-4">
                  {[
                    ["Model", forecast.model_name],
                    ["MAE", forecast.mae],
                    ["RMSE", forecast.rmse],
                    ["MAPE", `${forecast.mape}%`],
                  ].map(([k, v]) => (
                    <span key={k} className="inline-flex items-baseline gap-1 rounded-lg bg-slate-50 px-2.5 py-1 text-sm">
                      <span className="text-slate-500 text-xs">{k}</span>
                      <span className="font-semibold text-slate-800">{v}</span>
                    </span>
                  ))}
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={forecast.forecast_points}>
                    <defs>
                      <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#64748b" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#64748b" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="predictedFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} minTickGap={30} axisLine={{ stroke: "#e2e8f0" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ borderRadius: 10, border: "1px solid #e2e8f0", fontSize: 13, boxShadow: "0 4px 16px -4px rgb(15 23 42 / 0.15)" }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Area type="monotone" dataKey="actual" stroke="#64748b" fill="url(#actualFill)" strokeWidth={2} dot={false} name="Actual" />
                    <Area type="monotone" dataKey="predicted" stroke="#4f46e5" fill="url(#predictedFill)" strokeWidth={2} dot={false} name="Predicted" />
                  </AreaChart>
                </ResponsiveContainer>
                <Button variant="outline" icon={PlayCircle} onClick={runForecast} loading={busy} className="mt-4">
                  {busy ? "Re-training..." : "Re-run forecast"}
                </Button>
              </>
            )}
          </Card>
        </>
      ) : (
        <Card>
          <EmptyState icon={BarChart3} title="No sales data yet" description="Upload a CSV above to get started." />
        </Card>
      )}
    </div>
  );
}
