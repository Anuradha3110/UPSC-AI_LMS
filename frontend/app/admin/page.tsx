"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type PYQ = {
  id: string;
  year: number;
  paper: string;
  question_text: string;
  marks: number;
  marking_scheme: string | null;
};

type ContentItem = { id: string; title: string; source_type: string };

const PAPERS = ["GS1", "GS2", "GS3", "GS4", "CSAT", "ESSAY", "OPTIONAL"];

export default function AdminPage() {
  const [pyqs, setPyqs] = useState<PYQ[]>([]);
  const [content, setContent] = useState<ContentItem[]>([]);
  const [form, setForm] = useState({ year: 2024, paper: "GS2", question_text: "", marks: 15, marking_scheme: "" });
  const [error, setError] = useState<string | null>(null);

  function load() {
    apiFetch<PYQ[]>("/api/v1/cms/pyqs", { headers: authHeaders() }).then(setPyqs).catch(() => {});
    apiFetch<ContentItem[]>("/api/v1/content").then(setContent).catch(() => {});
  }
  useEffect(load, []);

  async function createPyq() {
    setError(null);
    try {
      await apiFetch("/api/v1/cms/pyqs", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ ...form, syllabus_node_ids: [], options: null, correct_option: null }),
      });
      setForm({ ...form, question_text: "", marking_scheme: "" });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create PYQ");
    }
  }

  async function deletePyq(id: string) {
    await apiFetch(`/api/v1/cms/pyqs/${id}`, { method: "DELETE", headers: authHeaders() });
    load();
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-8 px-6 py-10">
      <p className="page-eyebrow">MOD-11 · Content &amp; Marketing CMS</p>
      <h1 className="text-2xl font-semibold text-slate-900">Content Editor Console</h1>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="card">
        <p className="text-sm font-medium text-slate-900">Add a descriptive PYQ</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <input type="number" value={form.year} onChange={(e) => setForm({ ...form, year: Number(e.target.value) })} placeholder="Year" className="input !px-2 !py-1.5" />
          <select value={form.paper} onChange={(e) => setForm({ ...form, paper: e.target.value })} className="input !px-2 !py-1.5">
            {PAPERS.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <input type="number" value={form.marks} onChange={(e) => setForm({ ...form, marks: Number(e.target.value) })} placeholder="Marks" className="input !px-2 !py-1.5" />
        </div>
        <textarea value={form.question_text} onChange={(e) => setForm({ ...form, question_text: e.target.value })} placeholder="Question text" rows={2} className="input mt-2 w-full !px-2 !py-1.5" />
        <textarea value={form.marking_scheme} onChange={(e) => setForm({ ...form, marking_scheme: e.target.value })} placeholder="Marking scheme" rows={2} className="input mt-2 w-full !px-2 !py-1.5" />
        <button onClick={createPyq} className="btn-primary mt-3">Add PYQ</button>
      </div>

      <div>
        <p className="text-sm font-medium text-slate-900">PYQ bank ({pyqs.length})</p>
        <table className="mt-2 w-full text-sm">
          <tbody>
            {pyqs.slice(0, 30).map((q) => (
              <tr key={q.id} className="border-b border-slate-100">
                <td className="py-2 text-slate-500">{q.paper} · {q.year} · {q.marks}m</td>
                <td className="py-2">{q.question_text.slice(0, 60)}…</td>
                <td className="py-2 text-right">
                  <button onClick={() => deletePyq(q.id)} className="text-xs text-red-600 underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div>
        <p className="text-sm font-medium text-slate-900">Content items ({content.length})</p>
        <p className="text-xs text-slate-500">Full content CRUD via POST/DELETE /api/v1/content — this console lists the PYQ bank primarily; extend as needed.</p>
      </div>
    </main>
  );
}
