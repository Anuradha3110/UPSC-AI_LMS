"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, Bookmark, Highlighter, StickyNote } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type ContentSummary = {
  id: string;
  title: string;
  category: string | null;
  source_name: string | null;
  published_at: string | null;
} | null;

type BookmarkRow = { id: string; content_item_id: string; created_at: string; content: ContentSummary };
type AnnotationRow = {
  id: string;
  content_item_id: string;
  color: "yellow" | "green" | "blue" | "pink";
  selected_text: string;
  note_text: string | null;
  created_at: string;
  content: ContentSummary;
};
type ContinueReading = {
  content_item_id: string;
  progress_percent: number;
  content: ContentSummary;
} | null;

const COLOR_DOT: Record<string, string> = {
  yellow: "bg-yellow-400",
  green: "bg-green-500",
  blue: "bg-blue-500",
  pink: "bg-pink-500",
};

type Tab = "bookmarks" | "highlights" | "notes";

export default function StudyMaterialPage() {
  const [tab, setTab] = useState<Tab>("bookmarks");
  const [bookmarks, setBookmarks] = useState<BookmarkRow[]>([]);
  const [annotations, setAnnotations] = useState<AnnotationRow[]>([]);
  const [continueReading, setContinueReading] = useState<ContinueReading>(null);

  useEffect(() => {
    apiFetch<BookmarkRow[]>("/api/v1/study/bookmarks", { headers: authHeaders() })
      .then(setBookmarks)
      .catch(() => {});
    apiFetch<AnnotationRow[]>("/api/v1/study/annotations", { headers: authHeaders() })
      .then(setAnnotations)
      .catch(() => {});
    apiFetch<ContinueReading>("/api/v1/study/progress/continue", { headers: authHeaders() })
      .then(setContinueReading)
      .catch(() => {});
  }, []);

  const notes = annotations.filter((a) => a.note_text);

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">My Study Material</p>
      <h1 className="text-2xl font-semibold text-slate-900">Saved &amp; Annotated</h1>

      {continueReading?.content && (
        <Link
          href={`/current-affairs/${continueReading.content_item_id}`}
          className="card block transition-colors hover:border-brand-200 hover:bg-brand-50/40"
        >
          <p className="page-eyebrow">Continue Reading</p>
          <p className="mt-1 font-medium text-slate-900">{continueReading.content.title}</p>
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-brand-100">
            <div
              className="h-full rounded-full bg-brand-500"
              style={{ width: `${continueReading.progress_percent}%` }}
            />
          </div>
        </Link>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => setTab("bookmarks")}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "bookmarks" ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"
          }`}
        >
          <Bookmark className="h-3.5 w-3.5" /> Bookmarked ({bookmarks.length})
        </button>
        <button
          type="button"
          onClick={() => setTab("highlights")}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "highlights" ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"
          }`}
        >
          <Highlighter className="h-3.5 w-3.5" /> Highlights ({annotations.length})
        </button>
        <button
          type="button"
          onClick={() => setTab("notes")}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            tab === "notes" ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"
          }`}
        >
          <StickyNote className="h-3.5 w-3.5" /> Notes ({notes.length})
        </button>
      </div>

      {tab === "bookmarks" && (
        <div className="flex flex-col gap-3">
          {bookmarks.length === 0 && (
            <p className="card text-sm text-slate-500">No bookmarked articles yet.</p>
          )}
          {bookmarks.map((b) => (
            <Link
              key={b.id}
              href={`/current-affairs/${b.content_item_id}`}
              className="card flex items-center gap-3 transition-colors hover:border-brand-200 hover:bg-brand-50/40"
            >
              <BookOpen className="h-4 w-4 shrink-0 text-brand-500" />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-slate-900">{b.content?.title ?? "(article removed)"}</p>
                <p className="text-xs text-slate-500">
                  {b.content?.source_name}
                  {b.content?.published_at && ` · ${new Date(b.content.published_at).toLocaleDateString()}`}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}

      {tab === "highlights" && (
        <div className="flex flex-col gap-3">
          {annotations.length === 0 && (
            <p className="card text-sm text-slate-500">No highlights yet — select text on any article to highlight it.</p>
          )}
          {annotations.map((a) => (
            <Link
              key={a.id}
              href={`/current-affairs/${a.content_item_id}`}
              className="card block transition-colors hover:border-brand-200 hover:bg-brand-50/40"
            >
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${COLOR_DOT[a.color]}`} />
                <p className="truncate text-xs font-medium uppercase tracking-wide text-slate-400">
                  {a.content?.title ?? "(article removed)"}
                </p>
              </div>
              <p className="mt-1.5 text-sm italic text-slate-700">&ldquo;{a.selected_text}&rdquo;</p>
            </Link>
          ))}
        </div>
      )}

      {tab === "notes" && (
        <div className="flex flex-col gap-3">
          {notes.length === 0 && (
            <p className="card text-sm text-slate-500">No notes yet — add a note to any highlight.</p>
          )}
          {notes.map((a) => (
            <Link
              key={a.id}
              href={`/current-affairs/${a.content_item_id}`}
              className="card block transition-colors hover:border-brand-200 hover:bg-brand-50/40"
            >
              <p className="truncate text-xs font-medium uppercase tracking-wide text-slate-400">
                {a.content?.title ?? "(article removed)"}
              </p>
              <p className="mt-1.5 text-sm italic text-slate-500">&ldquo;{a.selected_text}&rdquo;</p>
              <p className="mt-2 rounded-md bg-brand-50 p-2 text-sm text-slate-700">{a.note_text}</p>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
