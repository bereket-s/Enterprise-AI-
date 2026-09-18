import { Card } from "./ui";

interface MetricSummary {
  mean: number;
  std: number;
}

type AlgorithmMetrics = Record<string, MetricSummary>;

interface SignificanceTest {
  test: string;
  compared: string;
  statistic: number | null;
  p_value: number | null;
  n_folds: number;
}

export interface EvaluationMetrics {
  [key: string]: number | AlgorithmMetrics | Record<string, AlgorithmMetrics> | SignificanceTest | undefined;
  cross_validation?: AlgorithmMetrics;
  algorithm_comparison?: Record<string, AlgorithmMetrics>;
  significance_test?: SignificanceTest;
}

function isMetricSummary(v: unknown): v is MetricSummary {
  return typeof v === "object" && v !== null && "mean" in v && "std" in v;
}

/** Every scalar top-level entry (precision, recall, roc_auc, ...rate_in_data) —
 * i.e. everything except the three structured keys handled separately below. */
function scalarEntries(metrics: EvaluationMetrics): [string, number][] {
  return Object.entries(metrics).filter((entry): entry is [string, number] => typeof entry[1] === "number");
}

/**
 * Renders a single-split scorecard alongside the 5-fold cross-validation and
 * multi-algorithm comparison added to address "single train/test split, no
 * statistical validation" as a methodology weakness (see report Chapter 3 §3.6
 * and Chapter 4's per-module evaluation tables).
 */
export function ModelEvaluationCard({ modelName, metrics }: { modelName: string; metrics: EvaluationMetrics }) {
  const scalars = scalarEntries(metrics);
  const cv = metrics.cross_validation;
  const comparison = metrics.algorithm_comparison;
  const sig = metrics.significance_test;
  const metricNames = comparison ? Object.keys(Object.values(comparison)[0] ?? {}) : [];

  return (
    <Card title={`Model: ${modelName}`}>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm mb-4">
        {scalars.map(([k, v]) => (
          <span key={k}>
            <span className="text-slate-500">{k}: </span>
            <span className="font-medium">{v}</span>
          </span>
        ))}
      </div>

      {cv && (
        <p className="text-xs text-slate-500 mb-3">
          5-fold cross-validated ROC-AUC: <span className="font-medium text-slate-700">{cv.roc_auc.mean} ± {cv.roc_auc.std}</span>
          {" "}(single-split figures above can vary by chance from one split to the next; this is the more reliable estimate).
        </p>
      )}

      {comparison && (
        <div className="overflow-x-auto">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
            Algorithm comparison (5-fold CV, mean ± std)
          </p>
          <table className="text-xs w-full">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="py-1 pr-4">Algorithm</th>
                {metricNames.map((m) => (
                  <th key={m} className="py-1 pr-4">{m}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(comparison).map(([algo, algoMetrics]) => (
                <tr key={algo} className="border-b border-slate-100">
                  <td className="py-1 pr-4 font-medium">{algo}</td>
                  {metricNames.map((m) => {
                    const cell = algoMetrics[m];
                    return (
                      <td key={m} className="py-1 pr-4">
                        {isMetricSummary(cell) ? `${cell.mean} ± ${cell.std}` : "—"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          {sig && (
            <p className="text-xs text-slate-400 mt-2">
              Wilcoxon signed-rank test ({sig.compared}, n={sig.n_folds} folds): p = {sig.p_value ?? "n/a"}
              {sig.p_value !== null && sig.p_value >= 0.05 ? " (not statistically significant at α=0.05)" : ""}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
