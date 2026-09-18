"use client";

import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton, RiskBadge } from "@/components/ui";
import { CsvUploadCard } from "@/components/CsvUploadCard";

interface ReorderRecommendation {
  id: number;
  product_sku: string;
  product_name: string;
  expected_demand: number;
  current_stock: number;
  recommended_order_qty: number;
  stockout_probability: number;
  risk_label: string;
}

export default function InventoryPage() {
  const [recs, setRecs] = useState<ReorderRecommendation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const resp = await api.get<ReorderRecommendation[]>("/api/inventory/reorder/latest");
      setRecs(resp.data);
    } catch {
      /* none yet */
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runAnalysis = async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await api.post<ReorderRecommendation[]>("/api/inventory/reorder/run");
      setRecs(resp.data);
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
          <h1 className="text-2xl font-semibold">Inventory & Procurement Optimization</h1>
          <p className="text-slate-500 text-sm mt-1">
            Demand-driven reorder points and purchase recommendations, built on your sales data.
          </p>
        </div>
        <PrimaryButton onClick={runAnalysis} disabled={busy}>
          {busy ? "Analyzing..." : "Run reorder analysis"}
        </PrimaryButton>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <CsvUploadCard module="inventory" onImported={load} />

      <Card>
        {recs.length === 0 ? (
          <p className="text-sm text-slate-500">
            No analysis yet. Make sure sales data has been uploaded in the BI module first, then run the analysis.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2">Product</th>
                <th className="py-2">Current stock</th>
                <th className="py-2">Expected demand (lead time)</th>
                <th className="py-2">Recommended order</th>
                <th className="py-2">Stockout risk</th>
              </tr>
            </thead>
            <tbody>
              {recs.map((r) => (
                <tr key={r.id} className="border-b border-slate-100">
                  <td className="py-2">{r.product_name}</td>
                  <td className="py-2">{r.current_stock}</td>
                  <td className="py-2">{r.expected_demand.toFixed(0)}</td>
                  <td className="py-2 font-medium">{r.recommended_order_qty.toFixed(0)}</td>
                  <td className="py-2">
                    <RiskBadge label={r.risk_label} /> <span className="text-slate-400 ml-1">{(r.stockout_probability * 100).toFixed(0)}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
