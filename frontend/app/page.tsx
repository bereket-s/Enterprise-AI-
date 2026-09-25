"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowRight,
  LineChart,
  Package,
  ShieldAlert,
  Sparkles,
  Users,
  Wrench,
  Cable,
  Bot,
  Lock,
} from "lucide-react";

const MODULES = [
  {
    icon: LineChart,
    name: "BI & Forecasting",
    description: "Sales KPIs, trend analysis, and ML-driven demand forecasting.",
  },
  {
    icon: Package,
    name: "Inventory & Procurement",
    description: "Reorder points, safety stock, and purchase recommendations.",
  },
  {
    icon: ShieldAlert,
    name: "Fraud & Anomaly Detection",
    description: "Transaction risk scoring with a built-in investigation workflow.",
  },
  {
    icon: Wrench,
    name: "Predictive Maintenance",
    description: "Equipment failure-risk prediction from live sensor data.",
  },
  {
    icon: Users,
    name: "Workforce Intelligence",
    description: "Configurable KPI scoring, goals, and attrition risk.",
  },
];

const HIGHLIGHTS = [
  { icon: Cable, title: "Six ways to connect data", description: "CSV upload, database connectors, REST push, scheduled sync, webhooks, and pre-built connectors." },
  { icon: Bot, title: "AI Copilot built in", description: "Ask plain-English questions and get answers grounded in your own live data — never hallucinated." },
  { icon: Lock, title: "Multi-tenant by design", description: "Strict per-organization data isolation with module-level access control out of the box." },
];

function fadeUp(delay = 0) {
  return {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] as const },
  };
}

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined" && window.localStorage.getItem("access_token")) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <main className="min-h-screen overflow-hidden bg-slate-50">
      {/* Nav */}
      <header className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-6 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
            <Sparkles size={18} className="text-white" strokeWidth={2.25} />
          </span>
          <span className="font-semibold text-slate-900 whitespace-nowrap">Enterprise AI</span>
        </div>
        <div className="flex items-center gap-1 sm:gap-3 shrink-0">
          <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors px-2.5 sm:px-3 py-2 whitespace-nowrap">
            Sign in
          </Link>
          <Link
            href="/register"
            className="text-sm font-medium bg-slate-900 text-white px-3.5 sm:px-4 py-2 rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap"
          >
            Get started
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <div className="absolute inset-0 -z-10 bg-grid [mask-image:radial-gradient(ellipse_60%_60%_at_50%_0%,black_10%,transparent_70%)]" />
        <div aria-hidden className="absolute -top-24 left-1/2 -translate-x-1/2 -z-10 h-[32rem] w-[32rem]">
          <div className="absolute top-0 left-0 h-72 w-72 rounded-full bg-brand-300/40 blur-3xl animate-blob" />
          <div className="absolute top-10 right-0 h-72 w-72 rounded-full bg-violet-300/30 blur-3xl animate-blob [animation-delay:4s]" />
          <div className="absolute bottom-0 left-24 h-72 w-72 rounded-full bg-sky-200/30 blur-3xl animate-blob [animation-delay:8s]" />
        </div>

        <div className="max-w-4xl mx-auto px-6 pt-16 pb-20 text-center">
          <motion.div {...fadeUp(0)} className="inline-flex items-center gap-1.5 rounded-full bg-white border border-slate-200 shadow-soft px-3 py-1 text-xs font-medium text-slate-600 mb-6">
            <Sparkles size={12} className="text-brand-600" />
            MSc Capstone · Enterprise AI Decision Intelligence
          </motion.div>
          <motion.h1 {...fadeUp(0.08)} className="text-4xl sm:text-5xl font-bold tracking-tight text-slate-900 leading-[1.1]">
            One platform for every
            <br />
            <span className="bg-gradient-to-r from-brand-600 via-violet-600 to-brand-500 bg-clip-text text-transparent">
              AI-driven business decision
            </span>
          </motion.h1>
          <motion.p {...fadeUp(0.16)} className="text-slate-600 max-w-xl mx-auto mt-5 text-lg">
            A modular, multi-tenant platform for predictive, prescriptive and anomaly-based
            business analytics — connect your data, turn on the modules you need.
          </motion.p>
          <motion.div {...fadeUp(0.24)} className="flex items-center justify-center gap-4 mt-9">
            <Link
              href="/register"
              className="group inline-flex items-center gap-2 px-5 py-3 rounded-lg bg-brand-600 text-white font-medium shadow-glow hover:bg-brand-700 transition-all"
            >
              Create an organization
              <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="/login"
              className="px-5 py-3 rounded-lg border border-slate-300 bg-white text-slate-700 font-medium hover:bg-slate-50 transition-colors"
            >
              Sign in
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Module grid */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true, margin: "-60px" }}
          className="text-center text-xs font-semibold tracking-widest text-slate-400 uppercase mb-6"
        >
          Five modules, one shared platform
        </motion.p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {MODULES.map((m, i) => (
            <motion.div
              key={m.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.06, ease: [0.16, 1, 0.3, 1] as const }}
              className="group bg-white rounded-xl border border-slate-200 shadow-card p-5 transition-all duration-200 hover:shadow-card-hover hover:-translate-y-1 hover:border-brand-200"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-600 mb-3 transition-transform duration-200 group-hover:scale-110">
                <m.icon size={20} strokeWidth={2} />
              </span>
              <p className="font-semibold text-sm text-slate-900">{m.name}</p>
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{m.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Highlights */}
      <section className="max-w-6xl mx-auto px-6 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {HIGHLIGHTS.map((h, i) => (
            <motion.div
              key={h.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-60px" }}
              transition={{ duration: 0.5, delay: i * 0.08 }}
              className="text-center sm:text-left"
            >
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-white mb-4">
                <h.icon size={20} strokeWidth={2} />
              </span>
              <p className="font-semibold text-slate-900">{h.title}</p>
              <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">{h.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-200 py-8">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
          <p>Enterprise AI Decision Intelligence Platform — MSc Capstone Project</p>
          <p>Every module can be enabled or disabled independently, per organization.</p>
        </div>
      </footer>
    </main>
  );
}
