"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Building2, Eye, EyeOff, Lock, Mail, User } from "lucide-react";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Alert, Button } from "@/components/ui";
import { AuthBrandPanel } from "@/components/AuthBrandPanel";

const INDUSTRIES = ["Retail", "Manufacturing", "Financial services", "Healthcare", "Technology", "Logistics", "Other"];
const SIZES = ["1-50", "51-200", "201-1000", "1000+"];

const inputClass =
  "w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm transition-shadow focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500";
const labelClass = "block text-sm font-medium text-slate-700 mb-1";

export default function RegisterPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [orgName, setOrgName] = useState("");
  const [industry, setIndustry] = useState(INDUSTRIES[0]);
  const [size, setSize] = useState(SIZES[0]);
  const [country, setCountry] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api.post("/api/auth/register", {
        organization: { name: orgName, industry, size, country: country || "unknown" },
        admin_email: email,
        admin_password: password,
        admin_full_name: fullName,
      });
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      const loginResp = await api.post("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      window.localStorage.setItem("access_token", loginResp.data.access_token);
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex">
      <AuthBrandPanel />

      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-slate-50">
        <motion.form
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] as const }}
          onSubmit={onSubmit}
          className="w-full max-w-md bg-white shadow-card rounded-2xl p-8 border border-slate-200"
        >
          <h1 className="text-xl font-bold text-slate-900">Create your organization</h1>
          <p className="text-sm text-slate-500 mt-1 mb-6">
            Every module starts enabled — turn off what you don&apos;t need from Settings.
          </p>

          {error && (
            <div className="mb-4">
              <Alert tone="error">{error}</Alert>
            </div>
          )}

          <label className={labelClass}>Company name</label>
          <div className="relative mb-4">
            <Building2 size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input required value={orgName} onChange={(e) => setOrgName(e.target.value)} className={`${inputClass} pl-9`} />
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className={labelClass}>Industry</label>
              <select value={industry} onChange={(e) => setIndustry(e.target.value)} className={inputClass}>
                {INDUSTRIES.map((i) => (
                  <option key={i} value={i}>
                    {i}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Size</label>
              <select value={size} onChange={(e) => setSize(e.target.value)} className={inputClass}>
                {SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s} employees
                  </option>
                ))}
              </select>
            </div>
          </div>

          <label className={labelClass}>Country</label>
          <input value={country} onChange={(e) => setCountry(e.target.value)} className={`${inputClass} mb-4`} />

          <hr className="my-5 border-slate-100" />

          <label className={labelClass}>Your full name</label>
          <div className="relative mb-4">
            <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className={`${inputClass} pl-9`} />
          </div>

          <label className={labelClass}>Admin email</label>
          <div className="relative mb-4">
            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={`${inputClass} pl-9`} />
          </div>

          <label className={labelClass}>Password</label>
          <div className="relative mb-6">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type={showPassword ? "text" : "password"}
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`${inputClass} pl-9 pr-9`}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          <Button type="submit" loading={loading} className="w-full py-2.5">
            {loading ? "Creating..." : "Create organization"}
          </Button>

          <p className="mt-5 text-sm text-slate-600 text-center">
            Already have an account?{" "}
            <Link href="/login" className="text-brand-700 font-medium hover:text-brand-800">
              Sign in
            </Link>
          </p>
        </motion.form>
      </div>
    </main>
  );
}
