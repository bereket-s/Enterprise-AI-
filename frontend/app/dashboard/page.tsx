"use client";

import { useAuth } from "@/lib/auth";
import { CopilotWidget } from "@/components/CopilotWidget";
import { Card } from "@/components/ui";

export default function OverviewPage() {
  const { user, modules } = useAuth();
  const enabled = modules.filter((m) => m.enabled);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user?.full_name}</h1>
        <p className="text-slate-500 text-sm mt-1">
          {enabled.length} of {modules.length} modules enabled for your organization.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {modules.map((m) => (
          <Card key={m.key}>
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{m.name}</p>
                <p className="text-sm text-slate-500 mt-1">{m.description}</p>
              </div>
              <span
                className={`text-xs rounded-full px-2.5 py-0.5 font-medium shrink-0 ${
                  m.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                }`}
              >
                {m.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-3 capitalize">{m.maturity} readiness</p>
          </Card>
        ))}
      </div>

      <CopilotWidget />
    </div>
  );
}
