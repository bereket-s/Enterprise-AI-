"use client";

import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton, RiskBadge } from "@/components/ui";
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

export default function FraudPage() {
  const [txns, setTxns] = useState<FraudTransaction[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
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
    load();
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Fraud & Anomaly Detection</h1>
          <p className="text-slate-500 text-sm mt-1">Transaction risk scoring with an investigation workflow.</p>
        </div>
        <PrimaryButton onClick={train} disabled={busy}>
          {busy ? "Training..." : "Train / retrain model"}
        </PrimaryButton>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <CsvUploadCard module="fraud" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName={evaluation.model_name} metrics={evaluation.metrics} />}

      <Card title="Highest-risk transactions">
        {txns.length === 0 ? (
          <p className="text-sm text-slate-500">No transactions scored yet. Train the model to get started.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2">Reference</th>
                <th className="py-2">Amount</th>
                <th className="py-2">Risk</th>
                <th className="py-2">Reasons</th>
                <th className="py-2">Status</th>
                <th className="py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {txns.map((t) => (
                <tr key={t.id} className="border-b border-slate-100 align-top">
                  <td className="py-2">{t.external_ref}</td>
                  <td className="py-2">${t.amount.toFixed(2)}</td>
                  <td className="py-2">
                    <RiskBadge label={t.risk_label} /> <span className="text-slate-400 ml-1">{(t.risk_score * 100).toFixed(0)}%</span>
                  </td>
                  <td className="py-2 text-xs text-slate-500 max-w-xs">{t.reason_codes.join("; ")}</td>
                  <td className="py-2 capitalize">{t.status}</td>
                  <td className="py-2 space-x-1 whitespace-nowrap">
                    <button onClick={() => setStatus(t.id, "investigating")} className="text-xs px-2 py-1 rounded border border-slate-300 hover:bg-slate-100">
                      Investigate
                    </button>
                    <button onClick={() => setStatus(t.id, "approved")} className="text-xs px-2 py-1 rounded border border-emerald-300 text-emerald-700 hover:bg-emerald-50">
                      Approve
                    </button>
                    <button onClick={() => setStatus(t.id, "blocked")} className="text-xs px-2 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50">
                      Block
                    </button>
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
