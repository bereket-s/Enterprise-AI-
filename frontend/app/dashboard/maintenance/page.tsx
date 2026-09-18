"use client";

import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton, RiskBadge } from "@/components/ui";
import { EvaluationMetrics, ModelEvaluationCard } from "@/components/ModelEvaluationCard";
import { CsvUploadCard } from "@/components/CsvUploadCard";

interface Equipment {
  id: number;
  external_ref: string;
  machine_type: string;
  failure_risk_score: number;
  risk_label: string;
  contributing_factors: string[];
}

interface Evaluation {
  model_name: string;
  metrics: EvaluationMetrics;
}

export default function MaintenancePage() {
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [eqResp, evalResp] = await Promise.allSettled([
        api.get<Equipment[]>("/api/maintenance/equipment"),
        api.get<Evaluation>("/api/maintenance/evaluation/latest"),
      ]);
      if (eqResp.status === "fulfilled") setEquipment(eqResp.value.data);
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
      await api.post("/api/maintenance/train");
      await load();
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
          <h1 className="text-2xl font-semibold">Predictive Maintenance</h1>
          <p className="text-slate-500 text-sm mt-1">Equipment failure-risk prediction from sensor readings.</p>
        </div>
        <PrimaryButton onClick={train} disabled={busy}>
          {busy ? "Training..." : "Train / retrain model"}
        </PrimaryButton>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <CsvUploadCard module="maintenance" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName={evaluation.model_name} metrics={evaluation.metrics} />}

      <Card title="Equipment to inspect first">
        {equipment.length === 0 ? (
          <p className="text-sm text-slate-500">No equipment scored yet. Train the model to get started.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2">Equipment</th>
                <th className="py-2">Type</th>
                <th className="py-2">Failure risk</th>
                <th className="py-2">Contributing factors</th>
              </tr>
            </thead>
            <tbody>
              {equipment.map((e) => (
                <tr key={e.id} className="border-b border-slate-100 align-top">
                  <td className="py-2">{e.external_ref}</td>
                  <td className="py-2">{e.machine_type}</td>
                  <td className="py-2">
                    <RiskBadge label={e.risk_label} /> <span className="text-slate-400 ml-1">{(e.failure_risk_score * 100).toFixed(0)}%</span>
                  </td>
                  <td className="py-2 text-xs text-slate-500 max-w-md">{e.contributing_factors.join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
