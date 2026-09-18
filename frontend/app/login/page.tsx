"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const form = new URLSearchParams();
      form.set("username", email);
      form.set("password", password);
      const resp = await api.post("/api/auth/login", form, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
      });
      window.localStorage.setItem("access_token", resp.data.access_token);
      await refreshUser();
      router.push("/dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <form onSubmit={onSubmit} className="w-full max-w-sm bg-white shadow rounded-xl p-8 border border-slate-200">
        <h1 className="text-xl font-semibold mb-6">Sign in</h1>
        {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
        <label className="block text-sm font-medium mb-1">Email</label>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <label className="block text-sm font-medium mb-1">Password</label>
        <input
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-6 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-brand-600 text-white py-2.5 font-medium hover:bg-brand-700 disabled:opacity-60"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
        <p className="mt-4 text-sm text-slate-600 text-center">
          No organization yet?{" "}
          <Link href="/register" className="text-brand-700 font-medium">
            Create one
          </Link>
        </p>
      </form>
    </main>
  );
}
