"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, ShieldAlert, ShieldCheck, ShieldX } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card, EmptyState, PageHeader, RiskBadge, SkeletonTable } from "@/components/ui";
import { ModelEvaluationCard, EvaluationMetrics } from "@/components/ModelEvaluationCard";
import { CsvUploadCard } from "@/components/CsvUploadCard";

interface FraudTransaction {
  id: number;
  external_ref: string;
  amount: number;
  risk_score: number;
  risk_label: string;
  reason_codes: string[];
  status: string;
}

interface Evaluation {
  model_name: string;
  metrics: EvaluationMetrics;
}

const STATUS_STYLES: Record<string, string> = {
  investigating: "bg-amber-100 text-amber-700",
  approved: "bg-emerald-100 text-emerald-700",
  blocked: "bg-red-100 text-red-700",
  open: "bg-slate-100 text-slate-600",
};

export default function FraudPage() {
  const [txns, setTxns] = useState<FraudTransaction[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [txnResp, evalResp] = await Promise.allSettled([
        api.get<FraudTransaction[]>("/api/fraud/transactions"),
        api.get<Evaluation>("/api/fraud/evaluation/latest"),
      ]);
      if (txnResp.status === "fulfilled") setTxns(txnResp.value.data);
      if (evalResp.status === "fulfilled") setEvaluation(evalResp.value.data);
    } catch {
      /* ignore */
    }
  };

  useEffect(() => {
    load().finally(() => setLoadingInitial(false));
  }, []);

  const train = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/fraud/train");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const setStatus = async (id: number, status: string) => {
    await api.put(`/api/fraud/transactions/${id}/status`, { status });
    setTxns((rows) => rows.map((r) => (r.id === id ? { ...r, status } : r)));
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={ShieldAlert}
        title="Fraud & Anomaly Detection"
        subtitle="Transaction risk scoring with an investigation workflow."
        actions={
          <Button icon={RefreshCw} onClick={train} loading={busy}>
            {busy ? "Training..." : "Train / retrain model"}
          </Button>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}

      <CsvUploadCard module="fraud" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName={evaluation.model_name} metrics={evaluation.metrics} />}

      <Card title="Highest-risk transactions" icon={AlertTriangle}>
        {loadingInitial ? (
          <SkeletonTable />
        ) : txns.length === 0 ? (
          <EmptyState icon={AlertTriangle} title="No transactions scored yet" description="Train the model to get started." />
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase tracking-wide border-b border-slate-200">
                  <th className="py-2.5 px-5 font-medium">Reference</th>
                  <th className="py-2.5 px-5 font-medium">Amount</th>
                  <th className="py-2.5 px-5 font-medium">Risk</th>
                  <th className="py-2.5 px-5 font-medium">Reasons</th>
                  <th className="py-2.5 px-5 font-medium">Status</th>
                  <th className="py-2.5 px-5 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {txns.map((t) => (
                  <tr key={t.id} className="border-b border-slate-100 last:border-0 align-top hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-5 font-medium text-slate-800">{t.external_ref}</td>
                    <td className="py-2.5 px-5">${t.amount.toFixed(2)}</td>
                    <td className="py-2.5 px-5">
                      <div className="flex items-center gap-1.5">
                        <RiskBadge label={t.risk_label} /> <span className="text-slate-400">{(t.risk_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-5 text-xs text-slate-500 max-w-xs">{t.reason_codes.join("; ")}</td>
                    <td className="py-2.5 px-5">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[t.status] ?? STATUS_STYLES.open}`}>
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-5 space-x-1 whitespace-nowrap">
                      <button
                        onClick={() => setStatus(t.id, "investigating")}
                        className="text-xs px-2 py-1 rounded-md border border-slate-300 hover:bg-slate-100 transition-colors inline-flex items-center gap-1"
                      >
                        Investigate
                      </button>
                      <button
                        onClick={() => setStatus(t.id, "approved")}
                        className="text-xs px-2 py-1 rounded-md border border-emerald-300 text-emerald-700 hover:bg-emerald-50 transition-colors inline-flex items-center gap-1"
                      >
                        <ShieldCheck size={12} /> Approve
                      </button>
                      <button
                        onClick={() => setStatus(t.id, "blocked")}
                        className="text-xs px-2 py-1 rounded-md border border-red-300 text-red-700 hover:bg-red-50 transition-colors inline-flex items-center gap-1"
                      >
                        <ShieldX size={12} /> Block
                      </button>
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
