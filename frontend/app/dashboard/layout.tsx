"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

const MODULE_ROUTES: Record<string, string> = {
  bi_forecasting: "/dashboard/bi",
  inventory: "/dashboard/inventory",
  fraud: "/dashboard/fraud",
  maintenance: "/dashboard/maintenance",
  workforce: "/dashboard/workforce",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, modules, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  // Close the mobile nav automatically on route change, so a tap on a link doesn't
  // leave the overlay open on top of the page it just navigated to.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500">Loading...</div>;
  }
  if (!user) return null;

  const enabledModules = modules.filter((m) => m.enabled);

  const navContent = (
    <>
      <div className="px-5 py-5 border-b border-slate-800">
        <p className="font-semibold leading-tight">Enterprise AI</p>
        <p className="text-xs text-slate-400">Decision Intelligence Platform</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <NavLink href="/dashboard" label="Overview" active={pathname === "/dashboard"} />
        {enabledModules.map((m) => (
          <NavLink
            key={m.key}
            href={MODULE_ROUTES[m.key]}
            label={m.name}
            active={pathname?.startsWith(MODULE_ROUTES[m.key])}
          />
        ))}
        {user.role === "org_admin" && (
          <NavLink href="/dashboard/settings" label="Settings & Modules" active={pathname === "/dashboard/settings"} />
        )}
      </nav>
      <div className="px-4 py-4 border-t border-slate-800 text-sm shrink-0">
        <p className="font-medium">{user.full_name}</p>
        <p className="text-slate-400 text-xs mb-3">{user.role.replace("_", " ")}</p>
        <button onClick={logout} className="text-slate-300 hover:text-white text-xs underline">
          Sign out
        </button>
      </div>
    </>
  );

  return (
    <div className="min-h-screen md:flex">
      {/* Mobile top bar: fixed sidebar width only made sense on desktop (see
          docs/architecture.md heuristic-walkthrough note) — below md we collapse
          the sidebar into a slide-over panel behind a hamburger button instead of
          permanently reserving 256px of a ~375px viewport. */}
      <div className="md:hidden flex items-center justify-between bg-slate-900 text-slate-100 px-4 py-3">
        <span className="font-semibold text-sm">Enterprise AI</span>
        <button
          onClick={() => setMobileNavOpen((v) => !v)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileNavOpen}
          className="p-2 -mr-2 text-slate-200"
        >
          {mobileNavOpen ? (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 4l12 12M16 4L4 16" strokeLinecap="round" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 5h14M3 10h14M3 15h14" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </div>

      {mobileNavOpen && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/40" onClick={() => setMobileNavOpen(false)}>
          <aside
            className="h-full w-64 max-w-[80vw] bg-slate-900 text-slate-100 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {navContent}
          </aside>
        </div>
      )}

      <aside className="hidden md:flex w-64 shrink-0 bg-slate-900 text-slate-100 flex-col">{navContent}</aside>

      <main className="flex-1 min-w-0 bg-slate-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">{children}</div>
      </main>
    </div>
  );
}

function NavLink({ href, label, active }: { href: string; label: string; active?: boolean }) {
  return (
    <Link
      href={href}
      className={`block rounded-md px-3 py-2 text-sm ${
        active ? "bg-brand-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
      }`}
    >
      {label}
    </Link>
  );
}
