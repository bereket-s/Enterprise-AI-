"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  Cable,
  Database,
  Key,
  Plug,
  RefreshCw,
  Timer,
  Trash2,
  Webhook as WebhookIcon,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { Alert, Badge, Button, Card, EmptyState, PageHeader } from "@/components/ui";

const MODULES = ["bi_forecasting", "inventory", "fraud", "maintenance", "workforce"];
// Neither has a trained model to retrain: BI is a recomputed forecast, Inventory is a
// deterministic reorder formula — both only ever make sense as "sync data", never "retrain".
const NOT_RETRAINABLE = new Set(["bi_forecasting", "inventory"]);

const inputClass =
  "rounded-lg border border-slate-300 px-3 py-1.5 text-sm transition-shadow focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500";
const linkBtn = "text-xs font-medium text-slate-500 hover:text-slate-800 hover:underline transition-colors";
const dangerLinkBtn = "text-xs font-medium text-red-600 hover:text-red-800 hover:underline transition-colors inline-flex items-center gap-1";

// ---------------------------------------------------------------- types
interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked: boolean;
}
interface DbConnection {
  id: number;
  module_key: string;
  name: string;
  dialect: string;
  host: string;
  port: number;
  database_name: string;
  username: string;
  source_query: string;
  last_synced_at: string | null;
  last_status: string | null;
}
interface ScheduledJob {
  id: number;
  module_key: string;
  job_type: string;
  connection_id: number | null;
  interval_minutes: number;
  enabled: boolean;
  last_run_at: string | null;
  last_status: string | null;
}
interface Webhook {
  id: number;
  module_key: string;
  token: string;
  created_at: string;
  last_received_at: string | null;
  receive_count: number;
}
interface ConnectorCatalogEntry {
  connector_type: string;
  display_name: string;
  modules: string[];
  description: string;
  status: string;
}
interface ConnectorInstance {
  id: number;
  connector_type: string;
  module_key: string;
  name: string;
  status: string;
  last_synced_at: string | null;
}

export default function IntegrationsPage() {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <PageHeader
        icon={Cable}
        title="Integrations"
        subtitle="Six ways to connect your data — pick whichever fits how your systems already work."
      />
      {error && <Alert tone="error">{error}</Alert>}
      {notice && <Alert tone="success">{notice}</Alert>}

      <ApiKeysSection setError={setError} setNotice={setNotice} />
      <DbConnectionsSection setError={setError} setNotice={setNotice} />
      <ScheduledJobsSection setError={setError} setNotice={setNotice} />
      <WebhooksSection setError={setError} setNotice={setNotice} />
      <ConnectorsSection setError={setError} setNotice={setNotice} />
      <ObservabilitySection setError={setError} />
    </div>
  );
}

type Setters = { setError: (s: string | null) => void; setNotice: (s: string | null) => void };

function SectionTitle({ n, icon: Icon, children }: { n: number; icon: LucideIcon; children: string }) {
  return (
    <h3 className="flex items-center gap-2.5 text-sm font-semibold text-slate-700 mb-3">
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
        <Icon size={16} strokeWidth={2} />
      </span>
      <Badge tone="brand">#{n}</Badge>
      {children}
    </h3>
  );
}

// ---------------------------------------------------------------- #3 API Keys (auth for push/connectors)
function ApiKeysSection({ setError, setNotice }: Setters) {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);

  const load = () => api.get<ApiKey[]>("/api/integrations/api-keys").then((r) => setKeys(r.data)).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setError(null);
    try {
      const resp = await api.post("/api/integrations/api-keys", { name: name || "Untitled key" });
      setNewKey(resp.data.raw_key);
      setName("");
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const revoke = async (id: number) => {
    await api.delete(`/api/integrations/api-keys/${id}`);
    load();
  };

  return (
    <Card>
      <SectionTitle n={3} icon={Key}>API Keys (used for REST push and connectors)</SectionTitle>
      <p className="text-sm text-slate-500 mb-3">
        Machine-to-machine credentials — your own system sends this in an <code className="text-xs bg-slate-100 rounded px-1 py-0.5">X-API-Key</code> header
        instead of a user login. Push data with:
      </p>
      <pre className="text-xs bg-slate-900 text-slate-100 rounded-lg p-3 mb-3 overflow-x-auto">
        {`curl -X POST ${process.env.NEXT_PUBLIC_API_BASE_URL}/api/integrations/push/bi_forecasting \\
  -H "X-API-Key: <your key>" -H "Content-Type: application/json" \\
  -d '{"records": [{"product_id": "SKU-1", "quantity": 5, "unit_price": 9.99, "transaction_date": "2024-01-01"}]}'`}
      </pre>

      {newKey && (
        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm animate-scale-in">
          <p className="font-medium mb-1">Copy this now — it won&apos;t be shown again:</p>
          <code className="break-all text-xs">{newKey}</code>
          <button onClick={() => setNewKey(null)} className="ml-3 text-xs underline">
            dismiss
          </button>
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Key name (e.g. 'Nightly ERP export')"
          className={`flex-1 ${inputClass}`}
        />
        <Button icon={Key} onClick={create}>Generate key</Button>
      </div>

      {keys.length === 0 ? (
        <EmptyState icon={Key} title="No API keys yet" />
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {keys.map((k) => (
              <tr key={k.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                <td className="py-2.5">{k.name}</td>
                <td className="py-2.5 text-slate-400 font-mono text-xs">{k.key_prefix}…</td>
                <td className="py-2.5 text-xs text-slate-400">{k.revoked ? "revoked" : k.last_used_at ? `used ${k.last_used_at.slice(0, 10)}` : "never used"}</td>
                <td className="py-2.5 text-right">
                  {!k.revoked && (
                    <button onClick={() => revoke(k.id)} className={dangerLinkBtn}>
                      <Trash2 size={12} /> Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- #2 Database Connector
function DbConnectionsSection({ setError, setNotice }: Setters) {
  const [items, setItems] = useState<DbConnection[]>([]);
  const [form, setForm] = useState({
    module_key: "bi_forecasting", name: "", dialect: "postgresql", host: "", port: 5432,
    database_name: "", username: "", password: "", source_query: "",
  });

  const load = () => api.get<DbConnection[]>("/api/integrations/db-connections").then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const create = async () => {
    setError(null);
    try {
      await api.post("/api/integrations/db-connections", form);
      setNotice("Database connection saved.");
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const test = async (id: number) => {
    setError(null);
    try {
      const resp = await api.post(`/api/integrations/db-connections/${id}/test`);
      setNotice(resp.data.ok ? "Connection succeeded." : `Connection failed: ${resp.data.message}`);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const sync = async (id: number) => {
    setError(null);
    try {
      const resp = await api.post(`/api/integrations/db-connections/${id}/sync`);
      setNotice(`Synced: ${JSON.stringify(resp.data)}`);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const remove = async (id: number) => {
    await api.delete(`/api/integrations/db-connections/${id}`);
    load();
  };

  return (
    <Card>
      <SectionTitle n={2} icon={Database}>Database Connector (read-only access to your own database)</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <select value={form.module_key} onChange={(e) => setForm({ ...form, module_key: e.target.value })} className={inputClass}>
          {MODULES.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className={inputClass} />
        <select value={form.dialect} onChange={(e) => setForm({ ...form, dialect: e.target.value })} className={inputClass}>
          <option value="postgresql">PostgreSQL</option>
          <option value="mysql">MySQL</option>
          <option value="mssql">SQL Server</option>
          <option value="oracle">Oracle</option>
          <option value="sqlite">SQLite (file path as host)</option>
        </select>
        <input placeholder="Host" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} className={inputClass} />
        <input type="number" placeholder="Port" value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 0 })} className={inputClass} />
        <input placeholder="Database name" value={form.database_name} onChange={(e) => setForm({ ...form, database_name: e.target.value })} className={inputClass} />
        <input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className={inputClass} />
        <input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputClass} />
        <input placeholder="Table name or SELECT query" value={form.source_query} onChange={(e) => setForm({ ...form, source_query: e.target.value })} className={`col-span-2 md:col-span-4 ${inputClass}`} />
      </div>
      <Button icon={Database} onClick={create} className="mb-4">Save connection</Button>

      {items.length === 0 ? (
        <EmptyState icon={Database} title="No database connections yet" />
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {items.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 last:border-0 align-top hover:bg-slate-50 transition-colors">
                <td className="py-2.5">{c.name} <span className="text-xs text-slate-400">({c.module_key})</span></td>
                <td className="py-2.5 text-xs text-slate-500">
                  {c.dialect === "sqlite" ? `sqlite:///${c.host}` : `${c.dialect}://${c.host}:${c.port}/${c.database_name}`}
                </td>
                <td className="py-2.5 text-xs text-slate-400 max-w-xs truncate">{c.last_status ?? "never synced"}</td>
                <td className="py-2.5 text-right space-x-3 whitespace-nowrap">
                  <button onClick={() => test(c.id)} className={linkBtn}>Test</button>
                  <button onClick={() => sync(c.id)} className={linkBtn}>Sync now</button>
                  <button onClick={() => remove(c.id)} className={dangerLinkBtn}>
                    <Trash2 size={12} /> Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- #4 Scheduled Sync / Retrain
function ScheduledJobsSection({ setError, setNotice }: Setters) {
  const [items, setItems] = useState<ScheduledJob[]>([]);
  const [connections, setConnections] = useState<DbConnection[]>([]);
  const [form, setForm] = useState({ module_key: "bi_forecasting", job_type: "retrain", connection_id: "", interval_minutes: 1440 });

  const load = () => {
    api.get<ScheduledJob[]>("/api/integrations/scheduled-jobs").then((r) => setItems(r.data)).catch(() => {});
    api.get<DbConnection[]>("/api/integrations/db-connections").then((r) => setConnections(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    setError(null);
    try {
      await api.post("/api/integrations/scheduled-jobs", {
        ...form,
        connection_id: form.connection_id ? parseInt(form.connection_id) : null,
      });
      setNotice("Scheduled job created.");
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const toggle = async (id: number, enabled: boolean) => {
    await api.put(`/api/integrations/scheduled-jobs/${id}`, { enabled });
    load();
  };
  const remove = async (id: number) => {
    await api.delete(`/api/integrations/scheduled-jobs/${id}`);
    load();
  };

  return (
    <Card>
      <SectionTitle n={4} icon={Timer}>Scheduled Sync &amp; Retraining (runs automatically in the background every ~60s tick)</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
        <select value={form.module_key} onChange={(e) => setForm({ ...form, module_key: e.target.value })} className={inputClass}>
          {MODULES.filter((m) => !NOT_RETRAINABLE.has(m) || form.job_type === "data_sync").map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select value={form.job_type} onChange={(e) => setForm({ ...form, job_type: e.target.value })} className={inputClass}>
          <option value="retrain">Retrain model</option>
          <option value="data_sync">Sync from database connection</option>
        </select>
        {form.job_type === "data_sync" && (
          <select value={form.connection_id} onChange={(e) => setForm({ ...form, connection_id: e.target.value })} className={inputClass}>
            <option value="">— select connection —</option>
            {connections.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
        <input type="number" value={form.interval_minutes} onChange={(e) => setForm({ ...form, interval_minutes: parseInt(e.target.value) || 60 })} className={inputClass} placeholder="Interval (minutes)" />
      </div>
      <Button icon={Timer} onClick={create} className="mb-4">Create schedule</Button>

      {items.length === 0 ? (
        <EmptyState icon={Timer} title="No scheduled jobs yet" />
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {items.map((j) => (
              <tr key={j.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                <td className="py-2.5">{j.job_type} <span className="text-xs text-slate-400">({j.module_key}, every {j.interval_minutes}m)</span></td>
                <td className="py-2.5 text-xs text-slate-400 max-w-xs truncate">{j.last_status ?? "not run yet"}</td>
                <td className="py-2.5 text-right space-x-3 whitespace-nowrap">
                  <button onClick={() => toggle(j.id, !j.enabled)} className={linkBtn}>{j.enabled ? "Disable" : "Enable"}</button>
                  <button onClick={() => remove(j.id)} className={dangerLinkBtn}>
                    <Trash2 size={12} /> Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- #5 Webhooks
function WebhooksSection({ setError, setNotice }: Setters) {
  const [items, setItems] = useState<Webhook[]>([]);
  const [moduleKey, setModuleKey] = useState("bi_forecasting");
  const [created, setCreated] = useState<{ url_path: string; secret: string } | null>(null);

  const load = () => api.get<Webhook[]>("/api/integrations/webhooks").then((r) => setItems(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    setError(null);
    try {
      const resp = await api.post("/api/integrations/webhooks", { module_key: moduleKey });
      setCreated({ url_path: resp.data.url_path, secret: resp.data.secret });
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const remove = async (id: number) => {
    await api.delete(`/api/integrations/webhooks/${id}`);
    load();
  };

  return (
    <Card>
      <SectionTitle n={5} icon={WebhookIcon}>Webhooks (your system pushes one event at a time, in real time)</SectionTitle>
      {created && (
        <div className="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm animate-scale-in">
          <p className="font-medium mb-1">Copy this now — the secret won&apos;t be shown again:</p>
          <p>URL: <code className="text-xs">{process.env.NEXT_PUBLIC_API_BASE_URL}{created.url_path}</code></p>
          <p>Secret: <code className="break-all text-xs">{created.secret}</code></p>
          <p className="text-xs text-slate-500 mt-1">
            Sign the raw JSON body with HMAC-SHA256 using this secret, send it as header <code className="bg-white/60 rounded px-1">X-Signature</code>.
          </p>
          <button onClick={() => setCreated(null)} className="mt-1 text-xs underline">dismiss</button>
        </div>
      )}
      <div className="flex gap-2 mb-4">
        <select value={moduleKey} onChange={(e) => setModuleKey(e.target.value)} className={inputClass}>
          {MODULES.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <Button icon={WebhookIcon} onClick={create}>Create webhook</Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={WebhookIcon} title="No webhooks yet" />
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {items.map((w) => (
              <tr key={w.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                <td className="py-2.5">{w.module_key}</td>
                <td className="py-2.5 text-xs text-slate-400">{w.receive_count} received{w.last_received_at ? `, last ${w.last_received_at.slice(0, 16)}` : ""}</td>
                <td className="py-2.5 text-right">
                  <button onClick={() => remove(w.id)} className={dangerLinkBtn}>
                    <Trash2 size={12} /> Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- #6 Pre-built Connectors
function ConnectorsSection({ setError, setNotice }: Setters) {
  const [catalog, setCatalog] = useState<ConnectorCatalogEntry[]>([]);
  const [instances, setInstances] = useState<ConnectorInstance[]>([]);

  const load = () => {
    api.get<ConnectorCatalogEntry[]>("/api/integrations/connectors/catalog").then((r) => setCatalog(r.data)).catch(() => {});
    api.get<ConnectorInstance[]>("/api/integrations/connectors").then((r) => setInstances(r.data)).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const connect = async (connector_type: string, module_key: string) => {
    setError(null);
    try {
      await api.post("/api/integrations/connectors", { connector_type, module_key, name: `${connector_type} — ${module_key}` });
      setNotice(`${connector_type} connected (simulated) for ${module_key}.`);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const sync = async (id: number) => {
    setError(null);
    try {
      const resp = await api.post(`/api/integrations/connectors/${id}/sync`);
      setNotice(`Synced: ${JSON.stringify(resp.data)}`);
      load();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  };
  const remove = async (id: number) => {
    await api.delete(`/api/integrations/connectors/${id}`);
    load();
  };

  return (
    <Card>
      <SectionTitle n={6} icon={Plug}>Pre-built Connectors</SectionTitle>
      <div className="mb-3">
        <Alert tone="warning">
          No real OAuth credentials exist for these third-party systems in this environment, so every connector
          below runs in <strong>simulated</strong> mode: it pulls a batch of rows shaped exactly like that
          system&apos;s real export, then goes through the same mapping and ingestion pipeline a live connection
          would use. Swapping in a real OAuth connection later only changes where the rows come from.
        </Alert>
      </div>
      <div className="grid md:grid-cols-2 gap-3 mb-4">
        {catalog.map((c) => (
          <div key={c.connector_type} className="border border-slate-200 rounded-lg p-3.5 hover:border-slate-300 transition-colors">
            <p className="font-medium text-sm flex items-center gap-1.5">
              {c.display_name} <Badge tone="amber">{c.status}</Badge>
            </p>
            <p className="text-xs text-slate-500 mb-2.5 mt-0.5">{c.description}</p>
            <div className="flex flex-wrap gap-1.5">
              {c.modules.map((m) => (
                <button
                  key={m}
                  onClick={() => connect(c.connector_type, m)}
                  disabled={c.connector_type === "generic_rest"}
                  className="text-xs rounded-full border border-slate-300 px-2.5 py-0.5 hover:bg-brand-50 hover:border-brand-200 hover:text-brand-700 transition-colors disabled:opacity-40"
                >
                  Connect to {m}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {instances.length === 0 ? (
        <EmptyState icon={Plug} title="No connectors set up yet" />
      ) : (
        <table className="w-full text-sm">
          <tbody>
            {instances.map((i) => (
              <tr key={i.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50 transition-colors">
                <td className="py-2.5">{i.name}</td>
                <td className="py-2.5"><Badge tone="amber">{i.status}</Badge></td>
                <td className="py-2.5 text-right space-x-3 whitespace-nowrap">
                  <button onClick={() => sync(i.id)} className={`${linkBtn} inline-flex items-center gap-1`}>
                    <RefreshCw size={12} /> Sync now
                  </button>
                  <button onClick={() => remove(i.id)} className={dangerLinkBtn}>
                    <Trash2 size={12} /> Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

// ---------------------------------------------------------------- Observability (audit log + usage)
function ObservabilitySection({ setError }: { setError: (s: string | null) => void }) {
  const [audit, setAudit] = useState<{ action: string; detail: unknown; created_at: string }[]>([]);
  const [usage, setUsage] = useState<{ module_key: string; day: string; request_count: number }[]>([]);

  useEffect(() => {
    api.get("/api/integrations/audit-log").then((r) => setAudit(r.data)).catch(() => {});
    api.get("/api/integrations/usage").then((r) => setUsage(r.data)).catch(() => {});
  }, []);

  return (
    <Card>
      <h3 className="flex items-center gap-2.5 text-sm font-semibold text-slate-700 mb-3">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
          <Activity size={16} strokeWidth={2} />
        </span>
        Observability: audit log &amp; usage
      </h3>
      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Recent admin actions</p>
          <ul className="text-xs space-y-1.5 max-h-48 overflow-y-auto">
            {audit.map((a, i) => (
              <li key={i} className="text-slate-600 flex items-center gap-1.5">
                <span className="text-slate-400 tabular-nums">{a.created_at.slice(0, 16)}</span>
                <span className="font-medium text-slate-700">{a.action}</span>
              </li>
            ))}
            {audit.length === 0 && <li className="text-slate-400">No actions logged yet.</li>}
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Per-module usage (requests/day)</p>
          <ul className="text-xs space-y-1.5 max-h-48 overflow-y-auto">
            {usage.map((u, i) => (
              <li key={i} className="text-slate-600 flex items-center gap-1.5">
                <span className="text-slate-400 tabular-nums">{u.day}</span>
                {u.module_key}: <span className="font-medium text-slate-700">{u.request_count}</span>
              </li>
            ))}
            {usage.length === 0 && <li className="text-slate-400">No usage recorded yet.</li>}
          </ul>
        </div>
      </div>
    </Card>
  );
}
