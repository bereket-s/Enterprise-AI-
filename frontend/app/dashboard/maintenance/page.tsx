"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Wrench, Gauge } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card, EmptyState, PageHeader, RiskBadge, SkeletonTable } from "@/components/ui";
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
  const [loadingInitial, setLoadingInitial] = useState(true);
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
    load().finally(() => setLoadingInitial(false));
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
      <PageHeader
        icon={Wrench}
        title="Predictive Maintenance"
        subtitle="Equipment failure-risk prediction from sensor readings."
        actions={
          <Button icon={RefreshCw} onClick={train} loading={busy}>
            {busy ? "Training..." : "Train / retrain model"}
          </Button>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}

      <CsvUploadCard module="maintenance" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName={evaluation.model_name} metrics={evaluation.metrics} />}

      <Card title="Equipment to inspect first" icon={Gauge}>
        {loadingInitial ? (
          <SkeletonTable />
        ) : equipment.length === 0 ? (
          <EmptyState icon={Gauge} title="No equipment scored yet" description="Train the model to get started." />
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase tracking-wide border-b border-slate-200">
                  <th className="py-2.5 px-5 font-medium">Equipment</th>
                  <th className="py-2.5 px-5 font-medium">Type</th>
                  <th className="py-2.5 px-5 font-medium">Failure risk</th>
                  <th className="py-2.5 px-5 font-medium">Contributing factors</th>
                </tr>
              </thead>
              <tbody>
                {equipment.map((e) => (
                  <tr key={e.id} className="border-b border-slate-100 last:border-0 align-top hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-5 font-medium text-slate-800">{e.external_ref}</td>
                    <td className="py-2.5 px-5">{e.machine_type}</td>
                    <td className="py-2.5 px-5">
                      <div className="flex items-center gap-1.5">
                        <RiskBadge label={e.risk_label} /> <span className="text-slate-400">{(e.failure_risk_score * 100).toFixed(0)}%</span>
                      </div>
                    </td>
                    <td className="py-2.5 px-5 text-xs text-slate-500 max-w-md">{e.contributing_factors.join("; ")}</td>
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
