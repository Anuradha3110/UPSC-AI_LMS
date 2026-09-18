"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { saveSession, type CurrentUser } from "@/lib/auth";

type TokenResponse = {
  access_token: string;
  user: CurrentUser;
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      saveSession(data.access_token, data.user);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen w-full bg-white">
      {/* Left brand panel — hidden on small screens, Coursera-style promo side */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-brand-800 px-12 py-12 text-white lg:flex">
        <div className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-brand-600 opacity-40 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 translate-x-1/3 translate-y-1/3 rounded-full bg-brand-500 opacity-50 blur-3xl" />

        <Link href="/" className="relative z-10 text-2xl font-bold tracking-tight">
          nirdesh
        </Link>

        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-semibold leading-snug">
            Prepare for the UPSC Civil Services Examination, with AI by your side.
          </h2>
          <p className="mt-4 text-sm text-blue-100">
            Personalised Mains evaluation, adaptive Prelims mocks and a syllabus tracker —
            all in one place.
          </p>
        </div>

        <p className="relative z-10 text-xs text-blue-200">
          © {new Date().getFullYear()} Nirdesh. AI-native UPSC preparation.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex w-full flex-col items-center justify-center px-6 py-16 lg:w-1/2">
        <div className="w-full max-w-sm">
          <Link href="/" className="mb-8 block text-xl font-bold tracking-tight text-brand-800 lg:hidden">
            nirdesh
          </Link>

          <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
          <p className="mt-1 text-sm text-slate-500">Log in to continue your preparation.</p>

          <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-5">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-700">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@example.com"
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input"
                placeholder="••••••••"
              />
            </label>

            {error && (
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}

            <button type="submit" disabled={loading} className="btn-primary mt-1">
              {loading ? "Logging in…" : "Log in"}
            </button>
          </form>

          <p className="mt-6 text-sm text-slate-600">
            New to Nirdesh?{" "}
            <Link href="/register" className="font-medium text-brand-600 hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}
