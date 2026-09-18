"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowUpRight, Bookmark, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";
import HighlightableText, { type Annotation } from "@/components/HighlightableText";
import { CATEGORY_LABEL } from "@/lib/categories";

type MCQ = {
  question_text: string;
  options: { label: string; text: string }[];
  correct_option: string;
  explanation: string;
};

type ContentItem = {
  id: string;
  title: string;
  body: string;
  source_url: string | null;
  source_name: string | null;
  tags: string[];
  published_at: string | null;
  category: string | null;
  prelims_facts: string[];
  mains_perspective: string | null;
  possible_questions: string[];
  mcq: MCQ | null;
};

export default function CurrentAffairsDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [item, setItem] = useState<ContentItem | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [bookmarked, setBookmarked] = useState(false);
  const [mcqSelected, setMcqSelected] = useState<string | null>(null);
  const progressSentRef = useRef(0);

  useEffect(() => {
    if (!id) return;
    apiFetch<ContentItem>(`/api/v1/content/${id}`).then(setItem).catch(() => {});
    apiFetch<Annotation[]>(`/api/v1/study/annotations?content_item_id=${id}`, {
      headers: authHeaders(),
    })
      .then(setAnnotations)
      .catch(() => {});
    apiFetch<{ content_item_id: string }[]>("/api/v1/study/bookmarks", { headers: authHeaders() })
      .then((rows) => setBookmarked(rows.some((r) => r.content_item_id === id)))
      .catch(() => {});
  }, [id]);

  const saveProgress = useCallback(
    (percent: number) => {
      if (!id) return;
      if (Math.abs(percent - progressSentRef.current) < 5) return;
      progressSentRef.current = percent;
      apiFetch(`/api/v1/study/progress/${id}`, {
        method: "PUT",
        headers: authHeaders(),
        body: JSON.stringify({ progress_percent: percent }),
      }).catch(() => {});
    },
    [id]
  );

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout> | null = null;
    function onScroll() {
      if (timeout) return;
      timeout = setTimeout(() => {
        timeout = null;
        const doc = document.documentElement;
        const scrollable = doc.scrollHeight - doc.clientHeight;
        const percent = scrollable > 0 ? Math.min(100, (window.scrollY / scrollable) * 100) : 100;
        saveProgress(Math.round(percent));
      }, 1500);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (timeout) clearTimeout(timeout);
    };
  }, [saveProgress]);

  async function toggleBookmark() {
    if (!id) return;
    if (bookmarked) {
      await apiFetch(`/api/v1/study/bookmarks/${id}`, { method: "DELETE", headers: authHeaders() });
      setBookmarked(false);
    } else {
      await apiFetch(`/api/v1/study/bookmarks?content_item_id=${id}`, {
        method: "POST",
        headers: authHeaders(),
      });
      setBookmarked(true);
    }
  }

  if (!item) {
    return (
      <main className="mx-auto max-w-2xl px-6 py-10">
        <p className="text-sm text-slate-500">Loading…</p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-6 py-10">
      <Link href="/current-affairs" className="inline-flex w-fit items-center gap-1.5 text-sm text-slate-500 hover:text-brand-600">
        <ArrowLeft className="h-4 w-4" /> Back to Current Affairs
      </Link>

      <div>
        <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
          {item.category && <span className="badge">{CATEGORY_LABEL[item.category] ?? item.category}</span>}
          {item.source_name && <span>{item.source_name}</span>}
          {item.published_at && <span>· {new Date(item.published_at).toLocaleDateString()}</span>}
        </div>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">{item.title}</h1>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={toggleBookmark}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors ${
              bookmarked
                ? "border-brand-200 bg-brand-50 text-brand-700"
                : "border-slate-200 text-slate-600 hover:bg-brand-50 hover:text-brand-700"
            }`}
          >
            <Bookmark className={`h-4 w-4 ${bookmarked ? "fill-brand-600 text-brand-600" : ""}`} />
            {bookmarked ? "Bookmarked" : "Bookmark"}
          </button>
          {item.source_url && (
            <a
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:underline"
            >
              Read full article <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>

      <div className="card">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Select text to highlight, add a note, or copy
        </p>
        <HighlightableText
          contentItemId={item.id}
          text={item.body}
          annotations={annotations}
          onAnnotationsChange={setAnnotations}
        />
      </div>

      {item.prelims_facts.length > 0 && (
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Prelims Key Facts</p>
          <ul className="mt-2 flex flex-col gap-1.5">
            {item.prelims_facts.map((f, i) => (
              <li key={i} className="flex gap-2 text-sm text-slate-700">
                <span className="text-brand-500">•</span> {f}
              </li>
            ))}
          </ul>
        </div>
      )}

      {item.mains_perspective && (
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Mains Perspective</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">{item.mains_perspective}</p>
        </div>
      )}

      {item.possible_questions.length > 0 && (
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Possible Mains Questions</p>
          <ul className="mt-2 flex flex-col gap-1.5">
            {item.possible_questions.map((q, i) => (
              <li key={i} className="text-sm text-slate-700">{i + 1}. {q}</li>
            ))}
          </ul>
        </div>
      )}

      {item.mcq && (
        <div className="card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Practice MCQ</p>
          <p className="mt-2 text-sm font-medium text-slate-900">{item.mcq.question_text}</p>
          <div className="mt-2 flex flex-col gap-1">
            {item.mcq.options.map((o) => {
              const isCorrect = mcqSelected && o.label === item.mcq!.correct_option;
              const isWrong = mcqSelected === o.label && o.label !== item.mcq!.correct_option;
              return (
                <button
                  key={o.label}
                  type="button"
                  onClick={() => setMcqSelected(o.label)}
                  className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    isCorrect
                      ? "border-green-300 bg-green-50 text-green-800"
                      : isWrong
                        ? "border-red-200 bg-red-50 text-red-700"
                        : "border-slate-200 hover:bg-brand-50/60"
                  }`}
                >
                  {isCorrect && <CheckCircle2 className="h-4 w-4 shrink-0" />}
                  {o.label}. {o.text}
                </button>
              );
            })}
          </div>
          {mcqSelected && (
            <p className="mt-3 text-sm text-slate-600">{item.mcq.explanation}</p>
          )}
        </div>
      )}

      {item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {item.tags.map((t) => (
            <span key={t} className="badge">{t}</span>
          ))}
        </div>
      )}
    </main>
  );
}
