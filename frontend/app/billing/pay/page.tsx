"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";
import { getPlan } from "@/lib/plans";

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window !== "undefined" && (window as any).Razorpay) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function PayPageInner() {
  const router = useRouter();
  const params = useSearchParams();
  const orderId = params.get("order") ?? "";
  const planId = params.get("plan") ?? "";
  const keyId = params.get("key") ?? "";
  const plan = getPlan(planId);

  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvv, setCvv] = useState("");
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openRazorpayCheckout() {
    setPaying(true);
    setError(null);
    const loaded = await loadRazorpayScript();
    if (!loaded) {
      setError("Failed to load Razorpay SDK. Please check your internet connection.");
      setPaying(false);
      return;
    }

    const options = {
      key: keyId,
      amount: (plan?.price ?? 0) * 100,
      currency: "INR",
      name: "Nirdesh UPSC LMS",
      description: `Plan Upgrade: ${plan?.label}`,
      order_id: orderId,
      handler: async function (response: {
        razorpay_payment_id: string;
        razorpay_order_id: string;
        razorpay_signature: string;
      }) {
        try {
          await apiFetch("/api/v1/billing/orders/verify", {
            method: "POST",
            headers: authHeaders(),
            body: JSON.stringify({
              order_id: response.razorpay_order_id || orderId,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
            }),
          });
          router.push("/billing?payment=success");
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Payment verification failed");
          setPaying(false);
        }
      },
      modal: {
        ondismiss: function () {
          setPaying(false);
        },
      },
      theme: { color: "#0f172a" },
    };

    const rzp = new (window as any).Razorpay(options);
    rzp.on("payment.failed", function (response: any) {
      setError(response.error?.description || "Payment failed");
      setPaying(false);
    });
    rzp.open();
  }

  async function payMock(e?: React.FormEvent) {
    e?.preventDefault();
    setPaying(true);
    setError(null);
    try {
      await apiFetch("/api/v1/billing/orders/verify", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ order_id: orderId }),
      });
      router.push("/billing?payment=success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment could not be verified");
    } finally {
      setPaying(false);
    }
  }

  if (!orderId || !plan) {
    return (
      <main className="mx-auto flex max-w-md flex-col gap-4 px-6 py-10">
        <p className="text-sm text-red-600">Missing or invalid order. Start checkout again from the billing page.</p>
        <Link href="/billing" className="btn-secondary w-fit">Back to Billing</Link>
      </main>
    );
  }

  const isFree = plan.price === 0;
  const isRazorpayLive = Boolean(keyId);

  return (
    <main className="mx-auto flex max-w-md flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-12 · Payment</p>
      <h1 className="text-2xl font-semibold text-slate-900">Confirm your plan</h1>

      <div className="card">
        <p className="font-medium text-slate-900">{plan.label}</p>
        <p className="text-sm text-slate-500">{plan.quota} AI gradings/period</p>
        <p className="mt-2 text-2xl font-semibold text-slate-900">₹{plan.price}</p>
        <p className="mt-1 text-xs text-slate-400">Order {orderId}</p>
      </div>

      <p className="text-xs text-slate-500">
        {isRazorpayLive
          ? "Click below to complete payment securely via Razorpay."
          : "Payments use sandbox order/verify in sandbox mode — no live card charge."}
      </p>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {isFree ? (
        <button onClick={() => payMock()} disabled={paying} className="btn-primary">
          {paying ? "Activating…" : "Activate plan"}
        </button>
      ) : isRazorpayLive ? (
        <button onClick={openRazorpayCheckout} disabled={paying} className="btn-primary w-full py-3 font-semibold">
          {paying ? "Opening Razorpay..." : `Pay ₹${plan.price} with Razorpay`}
        </button>
      ) : (
        <form onSubmit={payMock} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium text-slate-700">Card number</span>
            <input
              className="input"
              placeholder="4111 1111 1111 1111"
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value)}
              inputMode="numeric"
              required
            />
          </label>
          <div className="flex gap-4">
            <label className="flex flex-1 flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-700">Expiry</span>
              <input
                className="input"
                placeholder="MM/YY"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
                required
              />
            </label>
            <label className="flex flex-1 flex-col gap-1.5">
              <span className="text-sm font-medium text-slate-700">CVV</span>
              <input
                className="input"
                placeholder="123"
                value={cvv}
                onChange={(e) => setCvv(e.target.value)}
                inputMode="numeric"
                required
              />
            </label>
          </div>
          <button type="submit" disabled={paying} className="btn-primary">
            {paying ? "Processing…" : `Pay ₹${plan.price}`}
          </button>
        </form>
      )}

      <Link href="/billing" className="text-center text-sm text-slate-500 hover:underline">
        Cancel and go back
      </Link>
    </main>
  );
}

export default function PayPage() {
  return (
    <Suspense fallback={null}>
      <PayPageInner />
    </Suspense>
  );
}
