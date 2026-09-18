"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [orgName, setOrgName] = useState("");
  const [industry, setIndustry] = useState("retail");
  const [size, setSize] = useState("1-50");
  const [country, setCountry] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
    <main className="min-h-screen flex items-center justify-center px-6 py-12">
      <form onSubmit={onSubmit} className="w-full max-w-md bg-white shadow rounded-xl p-8 border border-slate-200">
        <h1 className="text-xl font-semibold mb-1">Create your organization</h1>
        <p className="text-sm text-slate-500 mb-6">
          Every module starts enabled — turn off what you don&apos;t need from Settings.
        </p>
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}

        <label className="block text-sm font-medium mb-1">Company name</label>
        <input required value={orgName} onChange={(e) => setOrgName(e.target.value)} className="w-full mb-4 rounded-md border border-slate-300 px-3 py-2 text-sm" />

        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Industry</label>
            <input value={industry} onChange={(e) => setIndustry(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Size</label>
            <input value={size} onChange={(e) => setSize(e.target.value)} className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" />
          </div>
        </div>

        <label className="block text-sm font-medium mb-1">Country</label>
        <input value={country} onChange={(e) => setCountry(e.target.value)} className="w-full mb-4 rounded-md border border-slate-300 px-3 py-2 text-sm" />

        <hr className="my-4" />

        <label className="block text-sm font-medium mb-1">Your full name</label>
        <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full mb-4 rounded-md border border-slate-300 px-3 py-2 text-sm" />

        <label className="block text-sm font-medium mb-1">Admin email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full mb-4 rounded-md border border-slate-300 px-3 py-2 text-sm" />

        <label className="block text-sm font-medium mb-1">Password</label>
        <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full mb-6 rounded-md border border-slate-300 px-3 py-2 text-sm" />

        <button type="submit" disabled={loading} className="w-full rounded-md bg-brand-600 text-white py-2.5 font-medium hover:bg-brand-700 disabled:opacity-60">
          {loading ? "Creating..." : "Create organization"}
        </button>
        <p className="mt-4 text-sm text-slate-600 text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-brand-700 font-medium">
            Sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
