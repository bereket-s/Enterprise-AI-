"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { LayoutDashboard, LogOut, Menu, Settings, Sparkles, X, type LucideIcon } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { MODULE_ICONS, MODULE_ROUTES } from "@/lib/moduleMeta";

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "U";
}

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
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400 gap-2">
        <Sparkles className="animate-pulse" size={18} />
        <span className="text-sm">Loading your workspace...</span>
      </div>
    );
  }
  if (!user) return null;

  const enabledModules = modules.filter((m) => m.enabled);

  const navContent = (
    <>
      <div className="px-5 py-5 border-b border-white/10 flex items-center gap-2.5">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
          <Sparkles size={18} className="text-white" strokeWidth={2.25} />
        </span>
        <div className="min-w-0">
          <p className="font-semibold leading-tight truncate">Enterprise AI</p>
          <p className="text-xs text-slate-400 truncate">Decision Intelligence</p>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <NavLink href="/dashboard" label="Overview" icon={LayoutDashboard} active={pathname === "/dashboard"} />
        {enabledModules.map((m) => (
          <NavLink
            key={m.key}
            href={MODULE_ROUTES[m.key]}
            label={m.name}
            icon={MODULE_ICONS[m.key]}
            active={pathname?.startsWith(MODULE_ROUTES[m.key])}
          />
        ))}
        {user.role === "org_admin" && (
          <>
            <div className="pt-3 mt-3 border-t border-white/10" />
            <NavLink href="/dashboard/settings" label="Settings & Modules" icon={Settings} active={pathname === "/dashboard/settings"} />
          </>
        )}
      </nav>
      <div className="px-4 py-4 border-t border-white/10 text-sm shrink-0">
        <div className="flex items-center gap-2.5 mb-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600/30 text-brand-100 text-xs font-semibold ring-1 ring-inset ring-white/10">
            {initials(user.full_name)}
          </span>
          <div className="min-w-0">
            <p className="font-medium truncate">{user.full_name}</p>
            <p className="text-slate-400 text-xs capitalize truncate">{user.role.replace("_", " ")}</p>
          </div>
        </div>
        <button onClick={logout} className="flex items-center gap-1.5 text-slate-400 hover:text-white text-xs transition-colors">
          <LogOut size={13} />
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
      <div className="md:hidden flex items-center justify-between bg-slate-900 text-slate-100 px-4 py-3 sticky top-0 z-30">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-brand-400 to-brand-600">
            <Sparkles size={14} className="text-white" />
          </span>
          <span className="font-semibold text-sm">Enterprise AI</span>
        </div>
        <button
          onClick={() => setMobileNavOpen((v) => !v)}
          aria-label="Toggle navigation menu"
          aria-expanded={mobileNavOpen}
          className="p-2 -mr-2 text-slate-200"
        >
          {mobileNavOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <AnimatePresence>
        {mobileNavOpen && (
          <motion.div
            className="md:hidden fixed inset-0 z-40 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setMobileNavOpen(false)}
          >
            <motion.aside
              className="h-full w-64 max-w-[80vw] bg-slate-900 text-slate-100 flex flex-col"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 28, stiffness: 260 }}
              onClick={(e) => e.stopPropagation()}
            >
              {navContent}
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <aside className="hidden md:flex w-64 shrink-0 bg-slate-900 text-slate-100 flex-col fixed inset-y-0">{navContent}</aside>

      <main className="flex-1 min-w-0 bg-slate-50 md:ml-64">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-8 py-6 md:py-8">{children}</div>
      </main>
    </div>
  );
}

function NavLink({ href, label, icon: Icon, active }: { href: string; label: string; icon?: LucideIcon; active?: boolean }) {
  return (
    <Link
      href={href}
      className={`group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors duration-150 ${
        active ? "bg-white/10 text-white font-medium" : "text-slate-300 hover:bg-white/5 hover:text-white"
      }`}
    >
      {active && (
        <motion.span
          layoutId="active-nav-indicator"
          className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-brand-400"
          transition={{ type: "spring", damping: 24, stiffness: 260 }}
        />
      )}
      {Icon && <Icon size={17} strokeWidth={2} className={active ? "text-brand-400" : "text-slate-400 group-hover:text-slate-200"} />}
      <span className="truncate">{label}</span>
    </Link>
  );
}
