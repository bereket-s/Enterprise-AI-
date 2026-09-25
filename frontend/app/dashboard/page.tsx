"use client";

import { ArrowUpRight } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { CopilotWidget } from "@/components/CopilotWidget";
import { MODULE_ICONS, MODULE_ROUTES } from "@/lib/moduleMeta";
import Link from "next/link";

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export default function OverviewPage() {
  const { user, modules } = useAuth();
  const enabled = modules.filter((m) => m.enabled);
  const firstName = user?.full_name?.split(" ")[0];

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          {greeting()}{firstName ? `, ${firstName}` : ""}
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          {enabled.length} of {modules.length} modules enabled for your organization.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {modules.map((m, i) => {
          const Icon = MODULE_ICONS[m.key];
          const href = MODULE_ROUTES[m.key];
          const body = (
            <>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3">
                  {Icon && (
                    <span
                      className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-transform duration-200 group-hover:scale-110 ${
                        m.enabled ? "bg-brand-50 text-brand-600" : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      <Icon size={19} strokeWidth={2} />
                    </span>
                  )}
                  <div>
                    <p className="font-semibold text-slate-900">{m.name}</p>
                    <p className="text-sm text-slate-500 mt-1">{m.description}</p>
                  </div>
                </div>
                <span
                  className={`text-xs rounded-full px-2.5 py-0.5 font-medium shrink-0 ${
                    m.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
                  }`}
                >
                  {m.enabled ? "Enabled" : "Disabled"}
                </span>
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="text-xs text-slate-400 capitalize">{m.maturity} readiness</p>
                {m.enabled && href && (
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 opacity-0 -translate-x-1 transition-all duration-200 group-hover:opacity-100 group-hover:translate-x-0">
                    Open
                    <ArrowUpRight size={13} />
                  </span>
                )}
              </div>
            </>
          );

          const cardClass =
            "group bg-white rounded-xl border border-slate-200 shadow-card p-5 animate-fade-in-up transition-all duration-200";

          return m.enabled && href ? (
            <Link
              key={m.key}
              href={href}
              style={{ animationDelay: `${i * 60}ms` }}
              className={`${cardClass} block hover:shadow-card-hover hover:-translate-y-0.5 hover:border-brand-200`}
            >
              {body}
            </Link>
          ) : (
            <div key={m.key} className={cardClass} style={{ animationDelay: `${i * 60}ms` }}>
              {body}
            </div>
          );
        })}
      </div>

      <CopilotWidget />
    </div>
  );
}
