"use client";

import { useEffect, useState } from "react";
import { ClipboardList, Package, PlayCircle } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card, EmptyState, PageHeader, RiskBadge, SkeletonTable } from "@/components/ui";
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
  const [loadingInitial, setLoadingInitial] = useState(true);
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
    load().finally(() => setLoadingInitial(false));
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
      <PageHeader
        icon={Package}
        title="Inventory & Procurement Optimization"
        subtitle="Demand-driven reorder points and purchase recommendations, built on your sales data."
        actions={
          <Button icon={PlayCircle} onClick={runAnalysis} loading={busy}>
            {busy ? "Analyzing..." : "Run reorder analysis"}
          </Button>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}

      <CsvUploadCard module="inventory" onImported={load} />

      <Card title="Reorder recommendations" icon={ClipboardList}>
        {loadingInitial ? (
          <SkeletonTable />
        ) : recs.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No analysis yet"
            description="Make sure sales data has been uploaded in the BI module first, then run the analysis."
          />
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase tracking-wide border-b border-slate-200">
                  <th className="py-2.5 px-5 font-medium">Product</th>
                  <th className="py-2.5 px-5 font-medium">Current stock</th>
                  <th className="py-2.5 px-5 font-medium">Expected demand (lead time)</th>
                  <th className="py-2.5 px-5 font-medium">Recommended order</th>
                  <th className="py-2.5 px-5 font-medium">Stockout risk</th>
                </tr>
              </thead>
              <tbody>
                {recs.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-5 font-medium text-slate-800">{r.product_name}</td>
                    <td className="py-2.5 px-5">{r.current_stock}</td>
                    <td className="py-2.5 px-5">{r.expected_demand.toFixed(0)}</td>
                    <td className="py-2.5 px-5 font-medium">{r.recommended_order_qty.toFixed(0)}</td>
                    <td className="py-2.5 px-5">
                      <div className="flex items-center gap-1.5">
                        <RiskBadge label={r.risk_label} /> <span className="text-slate-400">{(r.stockout_probability * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
