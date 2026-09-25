"use client";

import { DragEvent, useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, FileSpreadsheet, UploadCloud } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Button, Card } from "./ui";

interface Props {
  module: "bi" | "fraud" | "maintenance" | "workforce" | "inventory";
  onImported?: () => void;
}

const CANONICAL_FIELDS: Record<Props["module"], string[]> = {
  bi: ["product_id", "product_name", "quantity", "unit_price", "transaction_date", "customer_ref", "country"],
  fraud: ["transaction_ref", "amount", "timestamp", "account_ref", "merchant", "category", "customer_lat", "customer_long", "merchant_lat", "merchant_long", "is_fraud"],
  maintenance: ["equipment_ref", "machine_type", "temperature", "vibration", "pressure", "rotational_speed", "torque", "tool_wear", "failure"],
  workforce: ["employee_ref", "department", "job_role", "age", "monthly_income", "years_at_company", "job_satisfaction", "environment_satisfaction", "job_involvement", "years_since_last_promotion", "attrition"],
  inventory: ["product_id", "product_name", "current_stock", "supplier_lead_time_days"],
};

/** Upload-your-own-data card for Fraud/Maintenance/Workforce/Inventory — mirrors the
 * BI module's preview -> confirm mapping -> commit flow (integration method #1),
 * generalised to whatever a company's own export looks like rather than the
 * specific public dataset each module ships with for the demo. */
export function CsvUploadCard({ module, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<{ columns: string[]; suggested_mapping: Record<string, string | null> } | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
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

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) onFileSelected(f);
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
    <Card icon={UploadCloud} title="Bring your own data (CSV upload)">
      <p className="text-sm text-slate-500 mb-3">
        Upload a CSV with your own column names — we&apos;ll suggest a mapping to confirm before anything is imported.
      </p>
      {!preview && (
        <label
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center cursor-pointer transition-colors ${
            dragOver ? "border-brand-500 bg-brand-50" : "border-slate-200 hover:border-brand-300 hover:bg-slate-50"
          }`}
        >
          <span className={`flex h-10 w-10 items-center justify-center rounded-full ${dragOver ? "bg-brand-100 text-brand-600" : "bg-slate-100 text-slate-400"}`}>
            <UploadCloud size={20} />
          </span>
          <p className="text-sm font-medium text-slate-700">Drop a CSV file, or click to browse</p>
          <p className="text-xs text-slate-400">We auto-detect your columns</p>
          <input type="file" accept=".csv" hidden onChange={(e) => e.target.files && onFileSelected(e.target.files[0])} />
        </label>
      )}
      {result && (
        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} className="mt-3">
          <Alert tone="success">
            <span className="inline-flex items-center gap-1.5">
              <CheckCircle2 size={14} />
              {result}
            </span>
          </Alert>
        </motion.div>
      )}
      {error && (
        <div className="mt-3">
          <Alert tone="error">{error}</Alert>
        </div>
      )}

      {preview && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mt-3">
          <div className="flex items-center gap-2 text-sm text-slate-600 mb-4 bg-slate-50 rounded-lg px-3 py-2">
            <FileSpreadsheet size={15} className="text-brand-600 shrink-0" />
            <span className="truncate">{file?.name}</span>
            <span className="text-slate-400 shrink-0">· {preview.columns.length} columns detected</span>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            {fields.map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-slate-500 mb-1">{field}</label>
                <select
                  value={mapping[field] ?? ""}
                  onChange={(e) => setMapping((m) => ({ ...m, [field]: e.target.value }))}
                  className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm transition-shadow focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500"
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
          <div className="flex gap-2">
            <Button onClick={commitIngest} loading={busy}>
              {busy ? "Importing..." : "Import data"}
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setPreview(null);
                setFile(null);
              }}
            >
              Cancel
            </Button>
          </div>
        </motion.div>
      )}
    </Card>
  );
}
