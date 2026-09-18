"use client";

import { useState } from "react";
import { api, apiErrorMessage } from "@/lib/api";
import { Card, PrimaryButton } from "./ui";

interface Props {
  module: "fraud" | "maintenance" | "workforce" | "inventory";
  onImported?: () => void;
}

const CANONICAL_FIELDS: Record<Props["module"], string[]> = {
  fraud: ["transaction_ref", "amount", "timestamp", "account_ref", "merchant", "category", "customer_lat", "customer_long", "merchant_lat", "merchant_long", "is_fraud"],
  maintenance: ["equipment_ref", "machine_type", "temperature", "vibration", "pressure", "rotational_speed", "torque", "tool_wear", "failure"],
  workforce: ["employee_ref", "department", "job_role", "age", "monthly_income", "years_at_company", "job_satisfaction", "environment_satisfaction", "job_involvement", "years_since_last_promotion", "attrition"],
  inventory: ["product_id", "product_name", "current_stock", "supplier_lead_time_days"],
};

/** Upload-your-own-data card for Fraud/Maintenance/Workforce — mirrors the BI
 * module's preview -> confirm mapping -> commit flow (integration method #1),
 * generalised to whatever a company's own export looks like rather than the
 * specific public dataset each module ships with for the demo. */
export function CsvUploadCard({ module, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; suggested_mapping: Record<string, string | null> } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const fields = CANONICAL_FIELDS[module];

  const onFileSelected = async (f: File) => {
    setFile(f);
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append("file", f);
    try {
      const resp = await api.post(`/api/${module}/ingest/preview`, form);
      setPreview(resp.data);
      const initial: Record<string, string> = {};
      fields.forEach((field) => {
        if (resp.data.suggested_mapping[field]) initial[field] = resp.data.suggested_mapping[field];
      });
      setMapping(initial);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };

  const commitIngest = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("mapping", JSON.stringify(mapping));
      const resp = await api.post(`/api/${module}/ingest/commit`, form);
      setResult(`Imported ${resp.data.records_ingested} records.`);
      setPreview(null);
      setFile(null);
      onImported?.();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card title="Bring your own data (CSV upload)">
      <p className="text-sm text-slate-500 mb-3">
        Upload a CSV with your own column names — we&apos;ll suggest a mapping to confirm before anything is imported.
      </p>
      {!preview && (
        <label className="inline-block rounded-md border border-brand-600 text-brand-700 px-4 py-2 text-sm font-medium cursor-pointer hover:bg-brand-50">
          Upload CSV
          <input type="file" accept=".csv" hidden onChange={(e) => e.target.files && onFileSelected(e.target.files[0])} />
        </label>
      )}
      {result && <p className="text-sm text-emerald-700 mt-2">{result}</p>}
      {error && <p className="text-sm text-red-600 mt-2">{error}</p>}

      {preview && (
        <div className="mt-3">
          <div className="grid grid-cols-2 gap-3 mb-4">
            {fields.map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{field}</label>
                <select
                  value={mapping[field] ?? ""}
                  onChange={(e) => setMapping((m) => ({ ...m, [field]: e.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                >
                  <option value="">— not mapped —</option>
                  {preview.columns.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <PrimaryButton onClick={commitIngest} disabled={busy}>
            {busy ? "Importing..." : "Import data"}
          </PrimaryButton>
        </div>
      )}
    </Card>
  );
}
