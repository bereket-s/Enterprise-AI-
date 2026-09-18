"use client";

import { useEffect, useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton } from "@/components/ui";
import { EvaluationMetrics, ModelEvaluationCard } from "@/components/ModelEvaluationCard";
import { CsvUploadCard } from "@/components/CsvUploadCard";

interface Employee {
  id: number;
  external_ref: string;
  full_name: string;
  department: string;
  job_role: string;
  attrition_risk_score: number;
}

interface KPIWeight {
  department: string;
  kpi_name: string;
  weight: number;
}

interface PerformanceScore {
  employee_id: number;
  score: number;
  breakdown: Record<string, { normalized: number; weight: number; contribution: number }>;
  main_improvement_area: string | null;
}

interface Evaluation {
  metrics: EvaluationMetrics;
}

export default function WorkforcePage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [weights, setWeights] = useState<KPIWeight[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [scoreDetail, setScoreDetail] = useState<PerformanceScore | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const [empResp, weightResp, evalResp] = await Promise.allSettled([
      api.get<Employee[]>("/api/workforce/employees"),
      api.get<KPIWeight[]>("/api/workforce/kpi-weights"),
      api.get<Evaluation>("/api/workforce/attrition/evaluation/latest"),
    ]);
    if (empResp.status === "fulfilled") setEmployees(empResp.value.data);
    if (weightResp.status === "fulfilled") setWeights(weightResp.value.data);
    if (evalResp.status === "fulfilled") setEvaluation(evalResp.value.data);
  };

  useEffect(() => {
    load();
  }, []);

  const runScoring = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workforce/performance/run");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const trainAttrition = async () => {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/workforce/attrition/train");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const explainScore = async (employeeId: number) => {
    if (expanded === employeeId) {
      setExpanded(null);
      return;
    }
    try {
      const resp = await api.get<PerformanceScore>(`/api/workforce/performance/${employeeId}`);
      setScoreDetail(resp.data);
      setExpanded(employeeId);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  const updateWeight = async (department: string, kpiName: string, weight: number) => {
    await api.put(`/api/workforce/kpi-weights/${encodeURIComponent(department)}/${kpiName}`, { weight });
    setWeights((rows) => rows.map((r) => (r.department === department && r.kpi_name === kpiName ? { ...r, weight } : r)));
  };

  const byDepartment = weights.reduce<Record<string, KPIWeight[]>>((acc, w) => {
    (acc[w.department] ??= []).push(w);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Employee Performance & Workforce Intelligence</h1>
          <p className="text-slate-500 text-sm mt-1">Configurable KPI scoring, transparent breakdowns, and attrition risk.</p>
        </div>
        <div className="flex gap-2">
          <PrimaryButton onClick={runScoring} disabled={busy}>
            {busy ? "Working..." : "Run performance scoring"}
          </PrimaryButton>
          <PrimaryButton onClick={trainAttrition} disabled={busy} className="bg-slate-700 hover:bg-slate-800">
            Train attrition model
          </PrimaryButton>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <CsvUploadCard module="workforce" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName="XGBoost (attrition risk)" metrics={evaluation.metrics} />}

      <Card title="KPI weights by department">
        <p className="text-sm text-slate-500 mb-4">
          Each department weights performance differently — change a value and it applies the next time scoring runs.
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          {Object.entries(byDepartment).map(([dept, kpis]) => (
            <div key={dept} className="border border-slate-200 rounded-lg p-3">
              <p className="font-medium text-sm mb-2">{dept}</p>
              {kpis.map((k) => (
                <div key={k.kpi_name} className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-slate-600">{k.kpi_name.replace(/_/g, " ")}</span>
                  <input
                    type="number"
                    step={0.05}
                    min={0}
                    max={1}
                    value={k.weight}
                    onChange={(e) => updateWeight(dept, k.kpi_name, parseFloat(e.target.value))}
                    className="w-16 rounded border border-slate-300 px-1.5 py-0.5"
                  />
                </div>
              ))}
            </div>
          ))}
        </div>
      </Card>

      <Card title="Employees">
        {employees.length === 0 ? (
          <p className="text-sm text-slate-500">No employees loaded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-2">Employee</th>
                <th className="py-2">Department</th>
                <th className="py-2">Role</th>
                <th className="py-2">Attrition risk</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {employees.map((e) => (
                <tr key={e.id} className="border-b border-slate-100 align-top">
                  <td className="py-2">{e.full_name}</td>
                  <td className="py-2">{e.department}</td>
                  <td className="py-2">{e.job_role}</td>
                  <td className="py-2">{(e.attrition_risk_score * 100).toFixed(0)}%</td>
                  <td className="py-2">
                    <button onClick={() => explainScore(e.id)} className="text-xs text-brand-700 underline">
                      {expanded === e.id ? "Hide score" : "Explain my score"}
                    </button>
                    {expanded === e.id && scoreDetail && (
                      <div className="mt-2 bg-slate-50 rounded-md p-2 text-xs w-64">
                        <p className="font-semibold mb-1">Performance score: {scoreDetail.score}</p>
                        {Object.entries(scoreDetail.breakdown).map(([kpi, d]) => (
                          <div key={kpi} className="flex justify-between">
                            <span className="text-slate-500">{kpi.replace(/_/g, " ")}</span>
                            <span>{d.normalized} × {d.weight}</span>
                          </div>
                        ))}
                        {scoreDetail.main_improvement_area && (
                          <p className="mt-1 text-amber-700">
                            Main improvement area: {scoreDetail.main_improvement_area.replace(/_/g, " ")}
                          </p>
                        )}
                      </div>
                    )}
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
