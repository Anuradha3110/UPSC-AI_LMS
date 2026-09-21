"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";
import { getPlan } from "@/lib/plans";

type PendingOrder = { order_id: string; plan: string; key_id: string; mock?: boolean };

function readPendingOrder(): PendingOrder | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem("pending_order");
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.order_id || !parsed?.plan) return null;
    return {
      order_id: parsed.order_id,
      plan: parsed.plan,
      key_id: parsed.key_id ?? "",
      mock: parsed.mock ?? parsed.order_id.startsWith("order_mock_"),
    };
  } catch {
    return null;
  }
}

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
  const [pending, setPending] = useState<PendingOrder | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    setPending(readPendingOrder());
    setChecked(true);
  }, []);

  const orderId = pending?.order_id ?? "";
  const keyId = pending?.key_id ?? "";
  const plan = getPlan(pending?.plan ?? "");

  const [paying, setPaying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openRazorpayCheckout() {
    setPaying(true);
    setError(null);

    if (!keyId || keyId === "rzp_test_..." || keyId === "change-me") {
      setError(
        "Razorpay API Keys are invalid or missing in backend/.env. Please generate fresh API keys from https://dashboard.razorpay.com/app/keys."
      );
      setPaying(false);
      return;
    }

    const loaded = await loadRazorpayScript();
    if (!loaded) {
      setError("Failed to load payment gateway SDK. Please check your internet connection.");
      setPaying(false);
      return;
    }

    const options: any = {
      key: keyId,
      amount: (plan?.price ?? 0) * 100,
      currency: "INR",
      name: "Nirdesh UPSC LMS",
      description: `Plan Upgrade: ${plan?.label}`,
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
          sessionStorage.removeItem("pending_order");
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

    if (orderId && !orderId.startsWith("order_mock_")) {
      options.order_id = orderId;
    }

    try {
      const rzp = new (window as any).Razorpay(options);
      rzp.on("payment.failed", function (response: any) {
        setError(response.error?.description || "Payment failed");
        setPaying(false);
      });
      rzp.open();
    } catch (err: any) {
      setError(err?.message || "Could not launch Razorpay checkout");
      setPaying(false);
    }
  }

  async function confirmMockPayment() {
    setPaying(true);
    setError(null);
    try {
      await apiFetch("/api/v1/billing/orders/verify", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ order_id: orderId }),
      });
      sessionStorage.removeItem("pending_order");
      router.push("/billing?payment=success");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Payment could not be verified");
    } finally {
      setPaying(false);
    }
  }

  const isMockOrder = pending?.mock || orderId.startsWith("order_mock_") || !keyId || keyId === "rzp_test_..." || keyId === "change-me";

  async function handlePayment() {
    if (isMockOrder) {
      await confirmMockPayment();
    } else {
      await openRazorpayCheckout();
    }
  }

  if (!checked) {
    return null;
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
        Supported payment methods: UPI (Google Pay, PhonePe, Paytm, BHIM), QR Code, Credit/Debit Cards, Netbanking.
      </p>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <p className="font-medium">Checkout Notice</p>
          <p className="mt-1 text-xs">{error}</p>
        </div>
      )}

      {isFree ? (
        <button onClick={confirmMockPayment} disabled={paying} className="btn-primary w-full py-3.5 text-base font-semibold shadow-sm">
          {paying ? "Activating…" : "Activate plan"}
        </button>
      ) : (
        <button
          onClick={handlePayment}
          disabled={paying}
          className="btn-primary w-full py-3.5 text-base font-semibold shadow-sm"
        >
          {paying ? "Paying..." : "Pay Now"}
        </button>
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
