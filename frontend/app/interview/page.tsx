"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type DAF = {
  cadre_preference: string[];
  optional_subject: string;
  hobbies: string[];
  work_experience: string | null;
  home_district: string;
  home_state: string;
  graduation_field: string | null;
  extra_notes: string | null;
};

type Turn = { role: "panel" | "candidate"; text: string };
type Session = { id: string; status: string; transcript: Turn[]; feedback: string | null };

const emptyDaf: DAF = {
  cadre_preference: [],
  optional_subject: "",
  hobbies: [],
  work_experience: "",
  home_district: "",
  home_state: "",
  graduation_field: "",
  extra_notes: "",
};

export default function InterviewPage() {
  const [daf, setDaf] = useState<DAF>(emptyDaf);
  const [dafSaved, setDafSaved] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockedReason, setLockedReason] = useState<string | null>(null);

  // 402 means "not entitled" (require_plan("full_prep") on the backend) —
  // distinct from other failures, so it gets its own locked-state UI below
  // instead of a generic error line.
  function handleApiError(err: unknown, fallback: string) {
    if (err instanceof ApiError && err.status === 402) {
      setLockedReason(err.message);
      return;
    }
    setError(err instanceof ApiError ? err.message : fallback);
  }

  useEffect(() => {
    apiFetch<DAF | null>("/api/v1/interview/daf", { headers: authHeaders() })
      .then((d) => {
        if (d) {
          setDaf(d);
          setDafSaved(true);
        }
      })
      .catch((err) => handleApiError(err, "Could not load DAF"));
  }, []);

  async function saveDaf() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/v1/interview/daf", {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({
          ...daf,
          cadre_preference: typeof daf.cadre_preference === "string" ? (daf.cadre_preference as unknown as string).split(",").map((s) => s.trim()).filter(Boolean) : daf.cadre_preference,
          hobbies: typeof daf.hobbies === "string" ? (daf.hobbies as unknown as string).split(",").map((s) => s.trim()).filter(Boolean) : daf.hobbies,
        }),
      });
      setDafSaved(true);
    } catch (err) {
      handleApiError(err, "Could not save DAF");
    } finally {
      setBusy(false);
    }
  }

  async function startSession() {
    setBusy(true);
    setError(null);
    try {
      const s = await apiFetch<Session>("/api/v1/interview/sessions", { method: "POST", headers: authHeaders() });
      setSession(s);
    } catch (err) {
      handleApiError(err, "Could not start session");
    } finally {
      setBusy(false);
    }
  }

  async function sendReply() {
    if (!session || !reply.trim()) return;
    setBusy(true);
    try {
      const s = await apiFetch<Session>(`/api/v1/interview/sessions/${session.id}/reply`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ text: reply }),
      });
      setSession(s);
      setReply("");
    } finally {
      setBusy(false);
    }
  }

  async function endSession() {
    if (!session) return;
    setBusy(true);
    try {
      const s = await apiFetch<Session>(`/api/v1/interview/sessions/${session.id}/end`, {
        method: "POST",
        headers: authHeaders(),
      });
      setSession(s);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-08 · Personality Test Simulator</p>
      <h1 className="text-2xl font-semibold text-slate-900">Interview Simulator</h1>
      <p className="text-sm text-slate-600">Text-based panel round conditioned on your DAF. Voice articulation is a later-phase extension.</p>

      {lockedReason && (
        <div className="card border-amber-200 bg-amber-50">
          <p className="text-sm font-medium text-amber-900">Upgrade required</p>
          <p className="mt-1 text-xs text-amber-700">{lockedReason}</p>
          <Link href="/billing" className="btn-primary mt-2 inline-block w-fit">
            Go to Billing
          </Link>
        </div>
      )}

      {!lockedReason && !dafSaved && (
        <div className="card flex flex-col gap-2">
          <p className="text-sm font-medium text-slate-900">Fill in your DAF first</p>
          <input placeholder="Optional subject" value={daf.optional_subject} onChange={(e) => setDaf({ ...daf, optional_subject: e.target.value })} className="input !py-1.5" />
          <input placeholder="Cadre preference (comma-separated)" value={Array.isArray(daf.cadre_preference) ? daf.cadre_preference.join(", ") : daf.cadre_preference} onChange={(e) => setDaf({ ...daf, cadre_preference: e.target.value as unknown as string[] })} className="input !py-1.5" />
          <input placeholder="Hobbies (comma-separated)" value={Array.isArray(daf.hobbies) ? daf.hobbies.join(", ") : daf.hobbies} onChange={(e) => setDaf({ ...daf, hobbies: e.target.value as unknown as string[] })} className="input !py-1.5" />
          <input placeholder="Work experience" value={daf.work_experience ?? ""} onChange={(e) => setDaf({ ...daf, work_experience: e.target.value })} className="input !py-1.5" />
          <input placeholder="Home district" value={daf.home_district} onChange={(e) => setDaf({ ...daf, home_district: e.target.value })} className="input !py-1.5" />
          <input placeholder="Home state" value={daf.home_state} onChange={(e) => setDaf({ ...daf, home_state: e.target.value })} className="input !py-1.5" />
          <input placeholder="Graduation field" value={daf.graduation_field ?? ""} onChange={(e) => setDaf({ ...daf, graduation_field: e.target.value })} className="input !py-1.5" />
          <button onClick={saveDaf} disabled={busy} className="btn-primary mt-1 w-fit">
            {busy ? "Saving…" : "Save DAF"}
          </button>
        </div>
      )}

      {!lockedReason && dafSaved && !session && (
        <button onClick={startSession} disabled={busy} className="btn-primary w-fit">
          {busy ? "Starting…" : "Start interview session"}
        </button>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      {session && (
        <div className="flex flex-col gap-3">
          {session.transcript.map((t, i) => (
            <div key={i} className={t.role === "panel" ? "rounded-lg bg-brand-50 p-3" : "rounded-lg bg-brand-600 p-3 text-white"}>
              <p className="text-xs uppercase opacity-60">{t.role === "panel" ? "Panel" : "You"}</p>
              <p className="mt-1 text-sm">{t.text}</p>
            </div>
          ))}

          {session.status === "in_progress" && (
            <div className="flex gap-2">
              <input
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Your answer…"
                className="input flex-1"
              />
              <button onClick={sendReply} disabled={busy} className="btn-primary">
                Reply
              </button>
              <button onClick={endSession} disabled={busy} className="btn-secondary">
                End &amp; get feedback
              </button>
            </div>
          )}

          {session.feedback && (
            <div className="card">
              <p className="text-xs font-medium uppercase text-slate-500">Panel feedback</p>
              <p className="mt-2 whitespace-pre-line text-sm text-slate-700">{session.feedback}</p>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
