"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type Citation = { content_item_id: string; title: string; excerpt: string };
type Doubt = {
  id: string;
  question_text: string;
  ai_answer: string | null;
  citations: Citation[];
  confidence: string | null;
  status: string;
  mentor_response: string | null;
  created_at: string;
};

export default function DoubtsPage() {
  const [question, setQuestion] = useState("");
  const [doubts, setDoubts] = useState<Doubt[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<Doubt[]>("/api/v1/doubts", { headers: authHeaders() }).then(setDoubts).catch(() => {});
  }
  useEffect(load, []);

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/api/v1/doubts", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ question_text: question }),
      });
      setQuestion("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit doubt");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-07 · Doubt Resolution</p>
      <h1 className="text-2xl font-semibold text-slate-900">Ask a Conceptual Doubt</h1>
      <p className="text-sm text-slate-600">
        Answered against retrieved reading material with citations. Low-confidence answers auto-escalate to a mentor.
      </p>

      <div className="flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is the difference between Fundamental Rights and Directive Principles?"
          className="input flex-1"
        />
        <button onClick={ask} disabled={loading} className="btn-primary">
          {loading ? "Asking…" : "Ask"}
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-col gap-4">
        {doubts.map((d) => (
          <div key={d.id} className="card">
            <p className="font-medium text-slate-900">{d.question_text}</p>
            <p className="mt-1 text-xs uppercase text-slate-400">
              {d.status} {d.confidence && `· confidence: ${d.confidence}`}
            </p>
            {d.ai_answer && <p className="mt-2 text-sm text-slate-700">{d.ai_answer}</p>}
            {d.citations.length > 0 && (
              <div className="mt-2 flex flex-col gap-1">
                {d.citations.map((c) => (
                  <p key={c.content_item_id} className="text-xs text-slate-500">
                    <span className="font-medium">{c.title}:</span> {c.excerpt}
                  </p>
                ))}
              </div>
            )}
            {d.mentor_response && (
              <div className="mt-3 rounded-lg bg-brand-50 p-2">
                <p className="text-xs font-medium uppercase text-brand-700">Mentor response</p>
                <p className="mt-1 text-sm text-slate-700">{d.mentor_response}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </main>
  );
}
