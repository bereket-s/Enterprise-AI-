"use client";

import { LucideIcon, TrendingDown, TrendingUp } from "lucide-react";
import { ButtonHTMLAttributes, ReactNode } from "react";

// ---------------------------------------------------------------- Card

interface CardProps {
  title?: string;
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
  hover?: boolean;
  noAnimate?: boolean;
}

export function Card({ title, icon: Icon, children, className = "", hover = false, noAnimate = false }: CardProps) {
  return (
    <div
      className={`bg-white rounded-xl border border-slate-200 shadow-card p-5 ${
        !noAnimate ? "animate-fade-in-up" : ""
      } ${hover ? "transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5 hover:border-slate-300" : ""} ${className}`}
    >
      {title && (
        <h3 className="flex items-center gap-1.5 text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3">
          {Icon && <Icon size={14} className="text-slate-400" strokeWidth={2.25} />}
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- PageHeader

export function PageHeader({
  title,
  subtitle,
  icon: Icon,
  actions,
}: {
  title: string;
  subtitle?: string;
  icon?: LucideIcon;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between animate-fade-in-up">
      <div className="flex items-start gap-3">
        {Icon && (
          <span className="hidden sm:flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-inset ring-brand-100">
            <Icon size={22} strokeWidth={2} />
          </span>
        )}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="text-slate-500 text-sm mt-1 max-w-2xl">{subtitle}</p>}
        </div>
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

// ---------------------------------------------------------------- StatTile

export function StatTile({
  label,
  value,
  sublabel,
  icon: Icon,
  trend,
}: {
  label: string;
  value: string;
  sublabel?: string;
  icon?: LucideIcon;
  trend?: number;
}) {
  const trendPositive = typeof trend === "number" && trend >= 0;
  return (
    <div className="group bg-white rounded-xl border border-slate-200 shadow-card p-5 animate-fade-in-up transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-500">{label}</p>
        {Icon && (
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-600 transition-transform duration-200 group-hover:scale-110">
            <Icon size={16} strokeWidth={2.25} />
          </span>
        )}
      </div>
      <p className="text-2xl font-bold mt-1.5 tracking-tight text-slate-900">{value}</p>
      {(sublabel || typeof trend === "number") && (
        <div className="flex items-center gap-1.5 mt-1.5">
          {typeof trend === "number" && (
            <span
              className={`inline-flex items-center gap-0.5 text-xs font-semibold ${
                trendPositive ? "text-emerald-600" : "text-red-600"
              }`}
            >
              {trendPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
              {trendPositive ? "+" : ""}
              {trend}%
            </span>
          )}
          {sublabel && <p className="text-xs text-slate-400">{sublabel}</p>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- Badges

const RISK_STYLES: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-700",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};
const RISK_DOT: Record<string, string> = {
  low: "bg-emerald-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

export function RiskBadge({ label }: { label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        RISK_STYLES[label] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${RISK_DOT[label] ?? "bg-slate-400"}`} />
      {label}
    </span>
  );
}

export function Badge({ children, tone = "slate" }: { children: ReactNode; tone?: "slate" | "emerald" | "brand" | "amber" }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600",
    emerald: "bg-emerald-100 text-emerald-700",
    brand: "bg-brand-100 text-brand-700",
    amber: "bg-amber-100 text-amber-700",
  };
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}

// ---------------------------------------------------------------- Buttons

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: LucideIcon;
  loading?: boolean;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary: "bg-brand-600 text-white shadow-soft hover:bg-brand-700 hover:shadow-glow",
  secondary: "bg-slate-800 text-white hover:bg-slate-900",
  outline: "border border-brand-600 text-brand-700 hover:bg-brand-50",
  ghost: "text-slate-600 hover:bg-slate-100",
  danger: "border border-red-300 text-red-700 hover:bg-red-50",
};

export function Button({ variant = "primary", icon: Icon, loading, className = "", children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150 active:scale-[0.97] disabled:opacity-60 disabled:active:scale-100 ${VARIANT_STYLES[variant]} ${className}`}
    >
      {loading ? <Spinner className="h-3.5 w-3.5" /> : Icon ? <Icon size={15} strokeWidth={2.25} /> : null}
      {children}
    </button>
  );
}

/** Kept as an alias so existing call sites (`<PrimaryButton>`) keep working unchanged. */
export function PrimaryButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <Button variant="primary" {...props} />;
}

export function Spinner({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

// ---------------------------------------------------------------- Toggle

export function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <label className="inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only peer"
      />
      <div className="w-11 h-6 bg-slate-200 rounded-full peer peer-checked:bg-brand-600 transition-colors duration-200 relative peer-disabled:opacity-60">
        <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200 peer-checked:translate-x-5" />
      </div>
    </label>
  );
}

// ---------------------------------------------------------------- Alert

export function Alert({ tone = "error", children }: { tone?: "error" | "success" | "info" | "warning"; children: ReactNode }) {
  const styles: Record<string, string> = {
    error: "bg-red-50 text-red-700 border-red-200",
    success: "bg-emerald-50 text-emerald-700 border-emerald-200",
    info: "bg-brand-50 text-brand-700 border-brand-200",
    warning: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return (
    <div className={`animate-fade-in-up rounded-lg border px-4 py-2.5 text-sm ${styles[tone]}`} role={tone === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------- Empty state

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-6 animate-fade-in">
      {Icon && (
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 mb-3">
          <Icon size={22} strokeWidth={1.75} />
        </span>
      )}
      <p className="text-sm font-medium text-slate-700">{title}</p>
      {description && <p className="text-sm text-slate-500 mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

// ---------------------------------------------------------------- Skeletons

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonStatRow({ count = 3 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white rounded-xl border border-slate-200 shadow-card p-5">
          <Skeleton className="h-3.5 w-24 mb-3" />
          <Skeleton className="h-7 w-32 mb-2" />
          <Skeleton className="h-3 w-20" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-16" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
}
