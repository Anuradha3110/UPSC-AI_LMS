"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type RevisionItem = {
  id: string;
  syllabus_node_id: string;
  syllabus_node_title: string;
  next_due_at: string;
  interval: number;
  repetitions: number;
};

export default function RevisionPage() {
  const [items, setItems] = useState<RevisionItem[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  function load() {
    apiFetch<RevisionItem[]>("/api/v1/revision/due", { headers: authHeaders() })
      .then(setItems)
      .catch(() => {});
  }
  useEffect(load, []);

  async function review(nodeId: string, quality: number) {
    setBusy(nodeId);
    try {
      await apiFetch(`/api/v1/revision/${nodeId}/review`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ quality }),
      });
      load();
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-06 · Spaced Repetition</p>
      <h1 className="text-2xl font-semibold text-slate-900">Revision Queue</h1>
      <p className="text-sm text-slate-600">
        SM-2 scheduling, nudged by your recent graded-answer performance on the same topic.
      </p>

      {items.length === 0 && (
        <p className="card text-sm text-slate-500">
          Nothing due right now — visit <a href="/syllabus" className="text-brand-600 underline">Syllabus</a> to browse topics; they enter the queue once reviewed for the first time.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div key={item.id} className="card">
            <p className="font-medium text-slate-900">{item.syllabus_node_title}</p>
            <p className="text-xs text-slate-500">
              Interval {item.interval}d · {item.repetitions} successful review(s)
            </p>
            <p className="mt-2 text-xs uppercase text-slate-400">How well did you recall this?</p>
            <div className="mt-1 flex gap-1">
              {[0, 1, 2, 3, 4, 5].map((q) => (
                <button
                  key={q}
                  disabled={busy === item.syllabus_node_id}
                  onClick={() => review(item.syllabus_node_id, q)}
                  className="rounded-lg bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700 transition-colors hover:bg-brand-600 hover:text-white disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
