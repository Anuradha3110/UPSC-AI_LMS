"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { authHeaders, getUser, type CurrentUser } from "@/lib/auth";

type WeakTopic = {
  syllabus_node_id: string;
  syllabus_node_title: string;
  avg_score_ratio: number;
  attempts: number;
};

type PercentileEstimate = {
  estimate?: null;
  message?: string;
  latest_raw_score?: number;
  historical_cutoff_band?: { low: number; mid: number; high: number };
  read?: string;
};

type Subscription = {
  plan: string;
  ai_usage_quota: number;
  used_this_period: number;
  status: string;
};

const QUICK_LINKS: [string, string, string][] = [
  ["Syllabus", "/syllabus", "bg-brand-700"],
  ["Mains Practice", "/practice", "bg-brand-500"],
  ["Prelims Mock", "/tests/prelims", "bg-brand-800"],
  ["Revision Queue", "/revision", "bg-brand-400"],
  ["Current Affairs", "/current-affairs", "bg-brand-600"],
  ["Interview Sim", "/interview", "bg-brand-900"],
];

export default function DashboardPage() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [weak, setWeak] = useState<WeakTopic[]>([]);
  const [percentile, setPercentile] = useState<PercentileEstimate | null>(null);
  const [sub, setSub] = useState<Subscription | null>(null);

  useEffect(() => {
    const u = getUser();
    setUser(u);
    if (!u) return;
    apiFetch<WeakTopic[]>("/api/v1/analytics/me/weak-topics", { headers: authHeaders() })
      .then(setWeak)
      .catch(() => {});
    apiFetch<PercentileEstimate>("/api/v1/analytics/me/prelims-percentile", { headers: authHeaders() })
      .then(setPercentile)
      .catch(() => {});
    apiFetch<Subscription>("/api/v1/billing/me", { headers: authHeaders() })
      .then(setSub)
      .catch(() => {});
  }, []);

  if (!user) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-16">
        <p className="text-slate-600">
          Please <Link href="/login" className="text-brand-600 underline">log in</Link> first.
        </p>
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-brand-50/50">
      {/* Header band */}
      <div className="border-b border-slate-100 bg-white">
        <div className="mx-auto max-w-5xl px-6 py-8">
          <p className="page-eyebrow">My learning</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-900">Welcome back, {user.name}</h1>
          {user.optional_subject && (
            <p className="mt-1 text-sm text-slate-500">Optional subject: {user.optional_subject}</p>
          )}
        </div>
      </div>

      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-8">
        {/* Continue learning + subscription cards */}
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
            <div className="h-2 bg-brand-600" />
            <div className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Prelims GS1 estimate
              </p>
              {percentile?.read ? (
                <>
                  <p className="mt-2 text-3xl font-bold text-slate-900">{percentile.latest_raw_score}</p>
                  <p className="mt-1 text-sm text-slate-600">{percentile.read}</p>
                </>
              ) : (
                <>
                  <p className="mt-2 text-sm text-slate-500">{percentile?.message ?? "No data yet"}</p>
                  <Link href="/tests/prelims" className="btn-primary mt-4">
                    Take a mock
                  </Link>
                </>
              )}
            </div>
          </div>

          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
            <div className="h-2 bg-brand-400" />
            <div className="p-5">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Subscription</p>
              {sub ? (
                <>
                  <p className="mt-2 text-xl font-bold capitalize text-slate-900">
                    {sub.plan.replace(/_/g, " ")}
                  </p>
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>AI gradings used</span>
                      <span>
                        {sub.used_this_period}/{sub.ai_usage_quota}
                      </span>
                    </div>
                    <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-brand-100">
                      <div
                        className="h-full rounded-full bg-brand-500"
                        style={{
                          width: `${Math.min(
                            100,
                            sub.ai_usage_quota > 0
                              ? (sub.used_this_period / sub.ai_usage_quota) * 100
                              : 0
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                  <Link href="/billing" className="mt-4 inline-block text-sm font-medium text-brand-600 hover:underline">
                    Manage plan →
                  </Link>
                </>
              ) : (
                <p className="mt-2 text-sm text-slate-500">Loading…</p>
              )}
            </div>
          </div>
        </div>

        {/* Weak-topic progress */}
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Weak-topic heatmap (Mains)
          </p>
          {weak.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">
              No graded Mains answers yet —{" "}
              <Link href="/practice" className="text-brand-600 underline">
                write one
              </Link>
              .
            </p>
          ) : (
            <ul className="mt-3 flex flex-col divide-y divide-slate-100">
              {weak.slice(0, 8).map((w) => (
                <li key={w.syllabus_node_id} className="flex items-center gap-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-900">{w.syllabus_node_title}</p>
                    <p className="text-xs text-slate-500">{w.attempts} attempt(s)</p>
                  </div>
                  <div className="hidden h-1.5 w-32 overflow-hidden rounded-full bg-brand-100 sm:block">
                    <div
                      className="h-full rounded-full bg-brand-600"
                      style={{ width: `${Math.round(w.avg_score_ratio * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right text-sm font-semibold text-slate-900">
                    {(w.avg_score_ratio * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Quick links as course-style tiles */}
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Jump back in
          </p>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            {QUICK_LINKS.map(([label, href, color]) => (
              <Link
                key={href}
                href={href}
                className="group overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
              >
                <div className={`h-16 w-full ${color}`} />
                <div className="p-3.5">
                  <p className="text-sm font-semibold text-slate-900 group-hover:text-brand-600">
                    {label}
                  </p>
                  <p className="mt-0.5 text-xs text-slate-500">Continue →</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
