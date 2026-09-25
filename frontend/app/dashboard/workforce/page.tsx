"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BrainCircuit, PlayCircle, SlidersHorizontal, Users } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card, EmptyState, PageHeader, SkeletonTable } from "@/components/ui";
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

function riskColor(score: number) {
  if (score >= 0.66) return "text-red-600 bg-red-50";
  if (score >= 0.33) return "text-amber-600 bg-amber-50";
  return "text-emerald-600 bg-emerald-50";
}

export default function WorkforcePage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [weights, setWeights] = useState<KPIWeight[]>([]);
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [scoreDetail, setScoreDetail] = useState<PerformanceScore | null>(null);
  const [loadingInitial, setLoadingInitial] = useState(true);
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
    load().finally(() => setLoadingInitial(false));
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
      <PageHeader
        icon={Users}
        title="Employee Performance & Workforce Intelligence"
        subtitle="Configurable KPI scoring, transparent breakdowns, and attrition risk."
        actions={
          <>
            <Button variant="outline" icon={PlayCircle} onClick={runScoring} loading={busy}>
              {busy ? "Working..." : "Run performance scoring"}
            </Button>
            <Button variant="secondary" icon={BrainCircuit} onClick={trainAttrition} loading={busy}>
              Train attrition model
            </Button>
          </>
        }
      />

      {error && <Alert tone="error">{error}</Alert>}

      <CsvUploadCard module="workforce" onImported={load} />

      {evaluation && <ModelEvaluationCard modelName="XGBoost (attrition risk)" metrics={evaluation.metrics} />}

      <Card title="KPI weights by department" icon={SlidersHorizontal}>
        <p className="text-sm text-slate-500 mb-4">
          Each department weights performance differently — change a value and it applies the next time scoring runs.
        </p>
        {Object.keys(byDepartment).length === 0 ? (
          <p className="text-sm text-slate-500">No departments yet.</p>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {Object.entries(byDepartment).map(([dept, kpis]) => (
              <div key={dept} className="border border-slate-200 rounded-lg p-3.5 hover:border-slate-300 transition-colors">
                <p className="font-medium text-sm mb-2.5">{dept}</p>
                {kpis.map((k) => (
                  <div key={k.kpi_name} className="flex items-center justify-between text-xs mb-2">
                    <span className="text-slate-600">{k.kpi_name.replace(/_/g, " ")}</span>
                    <input
                      type="number"
                      step={0.05}
                      min={0}
                      max={1}
                      value={k.weight}
                      onChange={(e) => updateWeight(dept, k.kpi_name, parseFloat(e.target.value))}
                      className="w-16 rounded-md border border-slate-300 px-1.5 py-0.5 transition-shadow focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
                    />
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Employees" icon={Users}>
        {loadingInitial ? (
          <SkeletonTable />
        ) : employees.length === 0 ? (
          <EmptyState icon={Users} title="No employees loaded yet" description="Upload a CSV above to get started." />
        ) : (
          <div className="overflow-x-auto -mx-5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 uppercase tracking-wide border-b border-slate-200">
                  <th className="py-2.5 px-5 font-medium">Employee</th>
                  <th className="py-2.5 px-5 font-medium">Department</th>
                  <th className="py-2.5 px-5 font-medium">Role</th>
                  <th className="py-2.5 px-5 font-medium">Attrition risk</th>
                  <th className="py-2.5 px-5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {employees.map((e) => (
                  <tr key={e.id} className="border-b border-slate-100 last:border-0 align-top hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-5 font-medium text-slate-800">{e.full_name}</td>
                    <td className="py-2.5 px-5">{e.department}</td>
                    <td className="py-2.5 px-5">{e.job_role}</td>
                    <td className="py-2.5 px-5">
                      <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${riskColor(e.attrition_risk_score)}`}>
                        {(e.attrition_risk_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-5">
                      <button onClick={() => explainScore(e.id)} className="text-xs text-brand-700 underline hover:text-brand-800">
                        {expanded === e.id ? "Hide score" : "Explain my score"}
                      </button>
                      <AnimatePresence>
                        {expanded === e.id && scoreDetail && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-2 bg-slate-50 rounded-md p-2.5 text-xs w-64">
                              <p className="font-semibold mb-1.5">Performance score: {scoreDetail.score}</p>
                              {Object.entries(scoreDetail.breakdown).map(([kpi, d]) => (
                                <div key={kpi} className="flex justify-between py-0.5">
                                  <span className="text-slate-500">{kpi.replace(/_/g, " ")}</span>
                                  <span>{d.normalized} × {d.weight}</span>
                                </div>
                              ))}
                              {scoreDetail.main_improvement_area && (
                                <p className="mt-1.5 text-amber-700">
                                  Main improvement area: {scoreDetail.main_improvement_area.replace(/_/g, " ")}
                                </p>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
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
