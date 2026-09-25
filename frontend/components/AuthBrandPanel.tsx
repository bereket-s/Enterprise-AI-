"use client";

import { motion } from "framer-motion";
import { BarChart3, Bot, Cable, Shield, Sparkles } from "lucide-react";

const POINTS = [
  { icon: BarChart3, text: "Five production-ready AI modules" },
  { icon: Cable, text: "Six ways to connect your own data" },
  { icon: Bot, text: "AI Copilot grounded in your live metrics" },
  { icon: Shield, text: "Multi-tenant isolation, module by module" },
];

/** Shared branded side panel for the login/register split layout — hidden below md
 * so the form gets the full viewport on mobile instead of being squeezed. */
export function AuthBrandPanel() {
  return (
    <div className="hidden md:flex md:w-[42%] lg:w-[38%] relative overflow-hidden bg-slate-900 text-white flex-col justify-between p-10">
      <div aria-hidden className="absolute inset-0 bg-grid opacity-[0.06]" />
      <div aria-hidden className="absolute -top-32 -left-20 h-80 w-80 rounded-full bg-brand-500/30 blur-3xl animate-blob" />
      <div aria-hidden className="absolute bottom-0 right-0 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl animate-blob [animation-delay:6s]" />

      <div className="relative z-10 flex items-center gap-2.5">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 shadow-glow">
          <Sparkles size={18} className="text-white" strokeWidth={2.25} />
        </span>
        <span className="font-semibold">Enterprise AI</span>
      </div>

      <div className="relative z-10">
        <motion.h2
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-2xl font-bold leading-snug mb-6"
        >
          Decision intelligence for the whole business, in one workspace.
        </motion.h2>
        <div className="space-y-3.5">
          {POINTS.map((p, i) => (
            <motion.div
              key={p.text}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.15 + i * 0.08 }}
              className="flex items-center gap-3 text-sm text-slate-300"
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <p.icon size={15} strokeWidth={2} />
              </span>
              {p.text}
            </motion.div>
          ))}
        </div>
      </div>

      <p className="relative z-10 text-xs text-slate-500">MSc Capstone · Decision Intelligence Platform</p>
    </div>
  );
}
