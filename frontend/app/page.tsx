"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (typeof window !== "undefined" && window.localStorage.getItem("access_token")) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
      <h1 className="text-4xl font-bold text-brand-700 mb-3">Enterprise AI Decision Intelligence Platform</h1>
      <p className="text-slate-600 max-w-xl mb-8">
        A modular, multi-tenant platform for predictive, prescriptive and anomaly-based
        business analytics — connect your data, turn on the modules you need.
      </p>
      <div className="flex gap-4">
        <Link href="/login" className="px-5 py-2.5 rounded-lg bg-brand-600 text-white font-medium hover:bg-brand-700">
          Sign in
        </Link>
        <Link href="/register" className="px-5 py-2.5 rounded-lg border border-brand-600 text-brand-700 font-medium hover:bg-brand-50">
          Create an organization
        </Link>
      </div>
    </main>
  );
}
