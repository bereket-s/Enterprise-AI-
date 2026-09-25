"use client";

import Link from "next/link";
import { ArrowRight, Cable, SlidersHorizontal } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Alert, Card, PageHeader, Toggle } from "@/components/ui";
import { MODULE_ICONS } from "@/lib/moduleMeta";
import { useState } from "react";

export default function SettingsPage() {
  const { modules, refreshModules } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busyKey, setBusyKey] = useState<string | null>(null);

  const toggle = async (key: string, enabled: boolean) => {
    setBusyKey(key);
    setError(null);
    try {
      await api.put(`/api/org/modules/${key}`, { enabled });
      await refreshModules();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusyKey(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        icon={SlidersHorizontal}
        title="Settings & Modules"
        subtitle="Turn modules on or off for your organization. Disabled modules disappear from the sidebar and their API is blocked, even for admins, until re-enabled."
      />

      {error && <Alert tone="error">{error}</Alert>}

      <Card noAnimate>
        <div className="divide-y divide-slate-100">
          {modules.map((m, i) => {
            const Icon = MODULE_ICONS[m.key];
            return (
              <div
                key={m.key}
                style={{ animationDelay: `${i * 50}ms` }}
                className="animate-fade-in-up py-3.5 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {Icon && (
                    <span
                      className={`hidden sm:flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                        m.enabled ? "bg-brand-50 text-brand-600" : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      <Icon size={17} strokeWidth={2} />
                    </span>
                  )}
                  <div className="min-w-0">
                    <p className="font-medium text-sm">{m.name}</p>
                    <p className="text-xs text-slate-500 truncate">{m.description}</p>
                    <p className="text-xs text-slate-400 capitalize mt-0.5">{m.maturity} readiness</p>
                  </div>
                </div>
                <Toggle checked={m.enabled} disabled={busyKey === m.key} onChange={(v) => toggle(m.key, v)} />
              </div>
            );
          })}
        </div>
      </Card>

      <Card noAnimate>
        <Link href="/dashboard/settings/integrations" className="flex items-center justify-between gap-4 group">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Cable size={19} strokeWidth={2} />
            </span>
            <div>
              <p className="font-medium text-sm">Integrations</p>
              <p className="text-xs text-slate-500">
                Connect your own data: file upload, database connector, REST API push, scheduled sync,
                webhooks, and pre-built connectors.
              </p>
            </div>
          </div>
          <span className="flex items-center gap-1 text-sm text-brand-700 font-medium shrink-0 transition-transform group-hover:translate-x-0.5">
            Manage <ArrowRight size={15} />
          </span>
        </Link>
      </Card>
    </div>
  );
}
