"use client";

import Link from "next/link";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Card } from "@/components/ui";
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
      <div>
        <h1 className="text-2xl font-semibold">Settings & Modules</h1>
        <p className="text-slate-500 text-sm mt-1">
          Turn modules on or off for your organization. Disabled modules disappear from the sidebar and
          their API is blocked, even for admins, until re-enabled.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <Card>
        <div className="divide-y divide-slate-100">
          {modules.map((m) => (
            <div key={m.key} className="py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-sm">{m.name}</p>
                <p className="text-xs text-slate-500">{m.description}</p>
                <p className="text-xs text-slate-400 capitalize mt-0.5">{m.maturity} readiness</p>
              </div>
              <label className="inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={m.enabled}
                  disabled={busyKey === m.key}
                  onChange={(e) => toggle(m.key, e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 rounded-full peer peer-checked:bg-brand-600 transition-colors relative">
                  <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-5" />
                </div>
              </label>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-sm">Integrations</p>
            <p className="text-xs text-slate-500">
              Connect your own data: file upload, database connector, REST API push, scheduled sync,
              webhooks, and pre-built connectors.
            </p>
          </div>
          <Link href="/dashboard/settings/integrations" className="text-sm text-brand-700 font-medium underline">
            Manage integrations →
          </Link>
        </div>
      </Card>
    </div>
  );
}
