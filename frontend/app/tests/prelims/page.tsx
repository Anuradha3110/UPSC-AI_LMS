"use client";

import { useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type Option = { label: string; text: string };
type QuestionPreview = { id: string; question_text: string; marks: number; options: Option[] };
type MockTest = { id: string; paper: string; question_ids: string[]; questions_preview: QuestionPreview[] };
type AttemptResult = { raw_score: number; correct: number; wrong: number; unattempted: number; max_marks: number };

export default function PrelimsMockPage() {
  const [paper, setPaper] = useState<"GS1" | "CSAT">("GS1");
  const [count, setCount] = useState(20);
  const [test, setTest] = useState<MockTest | null>(null);
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function startTest() {
    setError(null);
    setResult(null);
    setResponses({});
    setLoading(true);
    try {
      const t = await apiFetch<MockTest>(`/api/v1/tests/prelims/mock?paper=${paper}&question_count=${count}`, {
        method: "POST",
        headers: authHeaders(),
      });
      setTest(t);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate a mock test");
    } finally {
      setLoading(false);
    }
  }

  async function submit() {
    if (!test) return;
    setLoading(true);
    setError(null);
    try {
      const r = await apiFetch<AttemptResult>("/api/v1/tests/prelims/submit", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ test_id: test.id, responses }),
      });
      setResult(r);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submission failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-04 · Prelims Test Engine</p>
      <h1 className="text-2xl font-semibold text-slate-900">Prelims Mock Test</h1>
      <p className="text-sm text-slate-600">Real UPSC rule: −⅓ mark per wrong answer, no penalty for skipping.</p>

      {!test && (
        <div className="card flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-700">
            Paper
            <select value={paper} onChange={(e) => setPaper(e.target.value as "GS1" | "CSAT")} className="input !py-1.5">
              <option value="GS1">GS Paper I</option>
              <option value="CSAT">CSAT</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-700">
            Questions
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={5}
              max={100}
              className="input w-20 !py-1.5"
            />
          </label>
          <button onClick={startTest} disabled={loading} className="btn-primary">
            {loading ? "Generating…" : "Start mock test"}
          </button>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {test && !result && (
        <div className="flex flex-col gap-4">
          {test.questions_preview.map((q, i) => (
            <div key={q.id} className="card">
              <p className="text-sm font-medium text-slate-900">{i + 1}. {q.question_text} <span className="text-slate-400">({q.marks}m)</span></p>
              <div className="mt-2 flex flex-col gap-1">
                {q.options.map((o) => (
                  <label key={o.label} className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="radio"
                      name={q.id}
                      checked={responses[q.id] === o.label}
                      onChange={() => setResponses((r) => ({ ...r, [q.id]: o.label }))}
                      className="accent-brand-600"
                    />
                    {o.label}. {o.text}
                  </label>
                ))}
              </div>
            </div>
          ))}
          <button onClick={submit} disabled={loading} className="btn-primary">
            {loading ? "Scoring…" : "Submit test"}
          </button>
        </div>
      )}

      {result && (
        <div className="card">
          <p className="text-2xl font-semibold text-slate-900">{result.raw_score} / {result.max_marks}</p>
          <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
            <dt className="text-slate-500">Correct</dt><dd>{result.correct}</dd>
            <dt className="text-slate-500">Wrong</dt><dd>{result.wrong}</dd>
            <dt className="text-slate-500">Unattempted</dt><dd>{result.unattempted}</dd>
          </dl>
          <button
            onClick={() => { setTest(null); setResult(null); }}
            className="btn-secondary mt-4"
          >
            Take another
          </button>
        </div>
      )}
    </main>
  );
}
