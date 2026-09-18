import Link from "next/link";

const MODULES = [
  ["Mains AI Evaluation", "Rubric-based, retrieval-grounded scoring of Essay, GS I–IV, and Optional answers — the same four dimensions a real examiner marks against."],
  ["Prelims Test Engine", "PYQ-calibrated mocks with the real −⅓ negative-marking rule, reported against historical cutoff bands."],
  ["Spaced-Repetition Revision", "SM-2 scheduling across the full 12–18 month cycle, nudged by your real graded-answer performance."],
  ["Current Affairs Digest", "PIB, PRS Bill Tracker, editorials, and the Economic Survey — compiled once, shared across every aspirant."],
  ["Interview Simulator", "A DAF-conditioned panel round with realistic follow-up questions and closing feedback."],
  ["Human-in-the-Loop Mentors", "Sampled AI grading reviewed by mentors — override rate is our own quality signal, not a guess."],
];

const PLANS = [
  ["Free Diagnostic", "₹0", "3 AI gradings/month — try the platform"],
  ["Prelims Only", "₹99/mo", "10 AI gradings/month — GS1 + CSAT focus"],
  ["Full Prep", "₹499/mo", "100 AI gradings/month — Prelims + Mains + Interview"],
];

export default function HomePage() {
  return (
    <main className="flex flex-col bg-white">
      <section className="relative overflow-hidden border-b border-slate-100 bg-brand-800 text-white">
        <div className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-brand-600 opacity-40 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 translate-x-1/3 translate-y-1/3 rounded-full bg-brand-500 opacity-40 blur-3xl" />
        <div className="relative mx-auto flex max-w-3xl flex-col gap-5 px-6 py-24">
          <p className="font-mono text-xs uppercase tracking-wide text-brand-200">
            Nirdesh · AI-Native UPSC Civil Services Prep
          </p>
          <h1 className="text-4xl font-semibold leading-tight">
            The exam is won or lost on the answer sheet.<br />So is this platform.
          </h1>
          <p className="max-w-xl text-blue-100">
            Most exam-prep apps are built for bubble tests. UPSC breaks that model
            at Mains — nine handwritten papers and a 275-mark interview. Nirdesh is
            an answer-evaluation system with a study platform around it, not the
            other way round.
          </p>
          <div className="flex gap-3">
            <Link href="/register" className="rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-brand-800 transition-colors hover:bg-brand-50">
              Start free
            </Link>
            <Link href="/login" className="rounded-lg border border-white/30 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-white/10">
              Log in
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-6 py-16">
        <h2 className="text-xl font-semibold text-slate-900">What's actually inside</h2>
        <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {MODULES.map(([title, body]) => (
            <div key={title} className="card transition-colors hover:border-brand-200">
              <p className="font-medium text-slate-900">{title}</p>
              <p className="mt-1 text-sm text-slate-600">{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-slate-100 bg-brand-50/50">
        <div className="mx-auto max-w-4xl px-6 py-16">
          <h2 className="text-xl font-semibold text-slate-900">Plans</h2>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            {PLANS.map(([name, price, desc]) => (
              <div key={name} className="card">
                <p className="font-medium text-slate-900">{name}</p>
                <p className="mt-1 text-2xl font-semibold text-brand-700">{price}</p>
                <p className="mt-2 text-sm text-slate-600">{desc}</p>
              </div>
            ))}
          </div>
          <Link href="/register" className="mt-6 inline-block text-sm font-medium text-brand-600 hover:underline">
            Compare plans in detail →
          </Link>
        </div>
      </section>

      <footer className="mx-auto w-full max-w-4xl px-6 py-10 text-xs text-slate-400">
        Nirdesh — built on Project Nirdesh System Architecture v1.0.
      </footer>
    </main>
  );
}
