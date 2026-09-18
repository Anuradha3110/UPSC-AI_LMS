"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders, getUser } from "@/lib/auth";

type Question = {
  id: string;
  paper: string;
  marks: number;
  question_text: string;
  optional_subject: string | null;
};

type Evaluation = {
  dimension_scores: {
    content_coverage: number;
    structure: number;
    word_limit_adherence: number;
    value_addition: number;
  };
  overall_score: number;
  max_marks: number;
  feedback_text: string;
  word_count: number;
  expected_word_limit: number;
};

type Submission = {
  id: string;
  pyq_id: string;
  status: string;
  submission_type: string;
  submitted_at: string;
  evaluation: Evaluation | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PAPERS = ["GS1", "GS2", "GS3", "GS4", "ESSAY", "OPTIONAL"];

export default function PracticePage() {
  const [paper, setPaper] = useState("GS2");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selected, setSelected] = useState<Question | null>(null);
  const [answer, setAnswer] = useState("");
  const [scanFile, setScanFile] = useState<File | null>(null);
  const [grading, setGrading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [history, setHistory] = useState<Submission[]>([]);

  useEffect(() => {
    const u = getUser();
    const params = new URLSearchParams({ paper });
    if (paper === "OPTIONAL" && u?.optional_subject) params.set("optional_subject", u.optional_subject);
    apiFetch<Question[]>(`/api/v1/answers/questions?${params}`)
      .then((qs) => {
        setQuestions(qs);
        setSelected(qs[0] ?? null);
      })
      .catch(() => setError("Could not load questions — is the backend running?"));
  }, [paper]);

  function loadHistory() {
    apiFetch<Submission[]>("/api/v1/answers", { headers: authHeaders() })
      .then(setHistory)
      .catch(() => {});
  }
  useEffect(loadHistory, []);

  async function pollUntilDone(id: string) {
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 1500));
      const s = await apiFetch<Submission>(`/api/v1/answers/${id}`, { headers: authHeaders() });
      if (s.status === "graded" || s.status === "grading_failed") {
        setSubmission(s);
        loadHistory();
        return;
      }
    }
  }

  async function handleSubmitTyped() {
    if (!selected) return;
    setGrading(true);
    setError(null);
    setSubmission(null);
    try {
      const result = await apiFetch<Submission>("/api/v1/answers/submit", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ pyq_id: selected.id, answer_text: answer }),
      });
      setSubmission(result);
      await pollUntilDone(result.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submission failed");
    } finally {
      setGrading(false);
    }
  }

  async function handleSubmitScan() {
    if (!selected || !scanFile) return;
    setGrading(true);
    setError(null);
    setSubmission(null);
    try {
      const form = new FormData();
      form.append("pyq_id", selected.id);
      form.append("image", scanFile);
      const res = await fetch(`${API_URL}/api/v1/answers/submit-scan`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new ApiError(res.status, body.detail ?? "Scan submission failed");
      }
      const result = (await res.json()) as Submission;
      setSubmission(result);
      await pollUntilDone(result.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Scan submission failed");
    } finally {
      setGrading(false);
    }
  }

  const wordCount = answer.trim() ? answer.trim().split(/\s+/).length : 0;

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">
        MOD-05 · Mains Answer-Writing Workspace
      </p>

      <div className="flex flex-wrap gap-2">
        {PAPERS.map((p) => (
          <button
            key={p}
            onClick={() => setPaper(p)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              paper === p ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <select
        value={selected?.id ?? ""}
        onChange={(e) => setSelected(questions.find((q) => q.id === e.target.value) ?? null)}
        className="input"
      >
        {questions.length === 0 && <option>No descriptive questions for this paper yet</option>}
        {questions.map((q) => (
          <option key={q.id} value={q.id}>
            [{q.marks}m] {q.question_text.slice(0, 80)}
          </option>
        ))}
      </select>

      {selected && (
        <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-4">
          <p className="text-xs font-medium text-slate-500">{selected.paper} · {selected.marks} marks</p>
          <p className="mt-1 font-medium text-slate-900">{selected.question_text}</p>
        </div>
      )}

      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        rows={12}
        placeholder="Write your answer here..."
        className="input font-serif text-[15px] leading-relaxed"
      />
      <p className="text-xs text-slate-500">{wordCount} words</p>

      <button
        onClick={handleSubmitTyped}
        disabled={grading || !answer.trim() || !selected}
        className="btn-primary"
      >
        {grading ? "Grading…" : "Submit typed answer for AI evaluation"}
      </button>

      <div className="rounded-xl border border-dashed border-brand-200 p-4">
        <p className="text-sm font-medium text-slate-900">Or upload a photo of a handwritten answer</p>
        <p className="text-xs text-slate-500">Transcribed via Claude vision (MOD-05&apos;s OCR intake path), then graded the same way.</p>
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setScanFile(e.target.files?.[0] ?? null)}
          className="mt-2 text-sm"
        />
        <button
          onClick={handleSubmitScan}
          disabled={grading || !scanFile || !selected}
          className="btn-secondary mt-2"
        >
          {grading ? "Working…" : "Upload & grade scan"}
        </button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {submission && (
        <div className="card">
          {submission.status !== "graded" && submission.status !== "grading_failed" && (
            <p className="text-sm text-slate-500">Status: {submission.status}…</p>
          )}
          {submission.status === "grading_failed" && (
            <p className="text-sm text-red-600">Grading failed — try again.</p>
          )}
          {submission.evaluation && (
            <>
              <p className="text-lg font-semibold text-slate-900">
                {submission.evaluation.overall_score} / {submission.evaluation.max_marks}
              </p>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <dt className="text-slate-500">Content coverage</dt>
                <dd>{submission.evaluation.dimension_scores.content_coverage} / 10</dd>
                <dt className="text-slate-500">Structure</dt>
                <dd>{submission.evaluation.dimension_scores.structure} / 10</dd>
                <dt className="text-slate-500">Word-limit adherence</dt>
                <dd>{submission.evaluation.dimension_scores.word_limit_adherence} / 10</dd>
                <dt className="text-slate-500">Value addition</dt>
                <dd>{submission.evaluation.dimension_scores.value_addition} / 10</dd>
              </dl>
              <p className="mt-3 text-sm text-slate-600">
                {submission.evaluation.word_count} words (limit {submission.evaluation.expected_word_limit})
              </p>
              <p className="mt-3 text-sm text-slate-700">{submission.evaluation.feedback_text}</p>
            </>
          )}
        </div>
      )}

      {history.length > 0 && (
        <div>
          <p className="text-xs font-medium uppercase text-slate-500">Your submission history</p>
          <table className="mt-2 w-full text-sm">
            <tbody>
              {history.slice(0, 10).map((h) => (
                <tr key={h.id} className="border-b border-slate-100">
                  <td className="py-2">{new Date(h.submitted_at).toLocaleDateString()}</td>
                  <td className="py-2 text-slate-500">{h.submission_type}</td>
                  <td className="py-2 text-right">
                    {h.evaluation ? `${h.evaluation.overall_score}/${h.evaluation.max_marks}` : h.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
