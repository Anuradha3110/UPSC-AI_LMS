"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";
import { PLANS } from "@/lib/plans";

type Subscription = {
  plan: string;
  ai_usage_quota: number;
  used_this_period: number;
  status: string;
  expires_at: string | null;
  razorpay_order_id: string | null;
};

function BillingPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const justPaid = params.get("payment") === "success";
  const [sub, setSub] = useState<Subscription | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<Subscription>("/api/v1/billing/me", { headers: authHeaders() }).then(setSub).catch(() => {});
  }
  useEffect(load, []);

  async function confirmOrder(orderId: string) {
    await apiFetch("/api/v1/billing/orders/verify", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ order_id: orderId }),
    });
    load();
  }

  async function choosePlan(plan: string) {
    setBusy(plan);
    setError(null);
    try {
      const order = await apiFetch<{ order_id: string; key_id?: string; mock?: boolean }>("/api/v1/billing/orders", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ plan }),
      });
      sessionStorage.setItem(
        "pending_order",
        JSON.stringify({
          order_id: order.order_id,
          plan,
          key_id: order.key_id ?? "",
          mock: order.mock ?? false,
        })
      );
      router.push("/billing/pay");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start checkout");
      setBusy(null);
    }
  }

  async function retryVerify(orderId: string) {
    setBusy(orderId);
    setError(null);
    try {
      await confirmOrder(orderId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not verify payment yet");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-12 · Billing &amp; Subscription</p>
      <h1 className="text-2xl font-semibold text-slate-900">Plan &amp; Usage</h1>
      <p className="text-xs text-slate-500">
        Supported payment options: UPI (Google Pay, PhonePe, Paytm, BHIM) &amp; Credit/Debit Cards.
      </p>

      {justPaid && (
        <div className="card border-green-200 bg-green-50">
          <p className="text-sm font-medium text-green-900">Payment successful — your plan is now active.</p>
        </div>
      )}

      {sub && (
        <div className="card">
          <p className="text-lg font-semibold capitalize text-slate-900">{sub.plan.replace(/_/g, " ")}</p>
          <p className="text-sm text-slate-600">{sub.used_this_period}/{sub.ai_usage_quota} AI gradings used this period</p>
          {sub.expires_at && (
            <p className="text-xs text-slate-500">Renews/expires {new Date(sub.expires_at).toLocaleDateString()}</p>
          )}
        </div>
      )}

      {sub?.status === "pending_payment" && sub.razorpay_order_id && (
        <div className="card border-amber-200 bg-amber-50">
          <p className="text-sm font-medium text-amber-900">Payment pending confirmation</p>
          <p className="mt-1 text-xs text-amber-700">
            We haven&apos;t confirmed this payment yet. If you completed checkout, verify it below.
          </p>
          <button
            onClick={() => retryVerify(sub.razorpay_order_id!)}
            disabled={busy === sub.razorpay_order_id}
            className="btn-primary mt-2"
          >
            {busy === sub.razorpay_order_id ? "Verifying…" : "Verify payment"}
          </button>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-3">
        {PLANS.map((p) => (
          <div key={p.id} className="card flex items-center justify-between">
            <div>
              <p className="font-medium text-slate-900">{p.label}</p>
              <p className="text-sm text-slate-500">₹{p.price} · {p.quota} AI gradings/period</p>
            </div>
            <button
              onClick={() => choosePlan(p.id)}
              disabled={busy === p.id || sub?.plan === p.id}
              className="btn-primary"
            >
              {sub?.plan === p.id ? "Current plan" : busy === p.id ? "Redirecting…" : "Choose"}
            </button>
          </div>
        ))}
      </div>
    </main>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={null}>
      <BillingPageInner />
    </Suspense>
  );
}
