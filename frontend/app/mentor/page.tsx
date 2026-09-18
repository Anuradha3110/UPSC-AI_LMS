"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type QueueItem = {
  id: string;
  question_text: string;
  answer_text: string;
  ai_dimension_scores: Record<string, number>;
  ai_overall_score: number;
};

type Doubt = { id: string; question_text: string; ai_answer: string | null };

export default function MentorPage() {
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [doubts, setDoubts] = useState<Doubt[]>([]);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [rationales, setRationales] = useState<Record<string, string>>({});
  const [responses, setResponses] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<QueueItem[]>("/api/v1/mentor/queue", { headers: authHeaders() }).then(setQueue).catch(() => {});
    apiFetch<Doubt[]>("/api/v1/mentor/doubts", { headers: authHeaders() }).then(setDoubts).catch(() => {});
  }
  useEffect(load, []);

  async function submitOverride(id: string) {
    setError(null);
    try {
      await apiFetch(`/api/v1/mentor/queue/${id}/override`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          override_score: Number(scores[id] ?? 0),
          override_rationale: rationales[id] ?? "",
        }),
      });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Override failed");
    }
  }

  async function submitResponse(id: string) {
    setError(null);
    try {
      await apiFetch(`/api/v1/mentor/doubts/${id}/respond?response_text=${encodeURIComponent(responses[id] ?? "")}`, {
        method: "POST",
        headers: authHeaders(),
      });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Response failed");
    }
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-10">
      <p className="page-eyebrow">MOD-07/09 · Mentor Console</p>
      <h1 className="text-2xl font-semibold text-slate-900">Mentor QA Queue</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-4">
        {queue.length === 0 && <p className="card text-sm text-slate-500">Nothing pending review.</p>}
        {queue.map((item) => (
          <div key={item.id} className="card">
            <p className="text-sm font-medium text-slate-900">{item.question_text}</p>
            <p className="mt-2 whitespace-pre-line text-sm text-slate-700">{item.answer_text}</p>
            <p className="mt-2 text-xs text-slate-500">
              AI score: {item.ai_overall_score} — {JSON.stringify(item.ai_dimension_scores)}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <input
                type="number"
                placeholder="Override score"
                value={scores[item.id] ?? ""}
                onChange={(e) => setScores({ ...scores, [item.id]: e.target.value })}
                className="input w-28 !py-1"
              />
              <input
                placeholder="Rationale"
                value={rationales[item.id] ?? ""}
                onChange={(e) => setRationales({ ...rationales, [item.id]: e.target.value })}
                className="input flex-1 !py-1"
              />
              <button onClick={() => submitOverride(item.id)} className="btn-primary !py-1.5">
                Submit override
              </button>
            </div>
          </div>
        ))}
      </div>

      <div>
        <h2 className="text-lg font-semibold text-slate-900">Escalated Doubts</h2>
        <div className="mt-3 flex flex-col gap-4">
          {doubts.length === 0 && <p className="card text-sm text-slate-500">None escalated.</p>}
          {doubts.map((d) => (
            <div key={d.id} className="card">
              <p className="text-sm font-medium text-slate-900">{d.question_text}</p>
              {d.ai_answer && <p className="mt-1 text-xs text-slate-500">AI attempted: {d.ai_answer}</p>}
              <div className="mt-2 flex gap-2">
                <input
                  placeholder="Your response"
                  value={responses[d.id] ?? ""}
                  onChange={(e) => setResponses({ ...responses, [d.id]: e.target.value })}
                  className="input flex-1 !py-1"
                />
                <button onClick={() => submitResponse(d.id)} className="btn-primary !py-1.5">
                  Respond
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
