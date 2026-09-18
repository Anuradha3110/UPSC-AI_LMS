"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Bookmark } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";
import { CATEGORIES, CATEGORY_LABEL } from "@/lib/categories";

type ContentItem = {
  id: string;
  title: string;
  body: string;
  source_type: string;
  source_url: string | null;
  source_name: string | null;
  tags: string[];
  published_at: string | null;
  category: string | null;
};

function isSameDay(a: Date, b: Date) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}

type View = "today" | "previous" | "monthly";

export default function CurrentAffairsPage() {
  const [items, setItems] = useState<ContentItem[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [view, setView] = useState<View>("today");
  const [category, setCategory] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<ContentItem[]>("/api/v1/content/digest?days=180").then(setItems).catch(() => {});
    apiFetch<{ content_item_id: string }[]>("/api/v1/study/bookmarks", { headers: authHeaders() })
      .then((rows) => setBookmarkedIds(new Set(rows.map((r) => r.content_item_id))))
      .catch(() => {});
  }, []);

  async function toggleBookmark(id: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (bookmarkedIds.has(id)) {
      await apiFetch(`/api/v1/study/bookmarks/${id}`, { method: "DELETE", headers: authHeaders() });
      setBookmarkedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    } else {
      await apiFetch(`/api/v1/study/bookmarks?content_item_id=${id}`, {
        method: "POST",
        headers: authHeaders(),
      });
      setBookmarkedIds((prev) => new Set(prev).add(id));
    }
  }

  const filtered = useMemo(
    () => (category ? items.filter((i) => i.category === category) : items),
    [items, category]
  );

  const today = new Date();
  const todayItems = filtered.filter((i) => i.published_at && isSameDay(new Date(i.published_at), today));
  const previousItems = filtered.filter((i) => !i.published_at || !isSameDay(new Date(i.published_at), today));

  const previousByDate = useMemo(() => {
    const groups = new Map<string, ContentItem[]>();
    for (const item of previousItems) {
      const key = item.published_at
        ? new Date(item.published_at).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })
        : "Undated";
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    return groups;
  }, [previousItems]);

  const monthlyGroups = useMemo(() => {
    const groups = new Map<string, ContentItem[]>();
    for (const item of filtered) {
      const key = item.published_at
        ? new Date(item.published_at).toLocaleDateString(undefined, { month: "long", year: "numeric" })
        : "Undated";
      groups.set(key, [...(groups.get(key) ?? []), item]);
    }
    return groups;
  }, [filtered]);

  const visibleGroups: [string, ContentItem[]][] =
    view === "today"
      ? todayItems.length > 0
        ? [["Today", todayItems]]
        : []
      : view === "previous"
        ? [...previousByDate.entries()]
        : [...monthlyGroups.entries()];

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-03 · Current Affairs</p>
      <h1 className="text-2xl font-semibold text-slate-900">Digest</h1>
      <p className="text-sm text-slate-600">
        AI-processed, daily-refreshed UPSC current affairs — open any article to read, highlight, and take notes.
      </p>

      <div className="flex gap-2">
        {(["today", "previous", "monthly"] as View[]).map((v) => (
          <button
            key={v}
            type="button"
            onClick={() => setView(v)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
              view === v ? "bg-brand-600 text-white" : "bg-brand-50 text-brand-700 hover:bg-brand-100"
            }`}
          >
            {v === "previous" ? "Previous Days" : v === "monthly" ? "Monthly" : "Today"}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => setCategory(null)}
          className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
            category === null ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
          }`}
        >
          All
        </button>
        {CATEGORIES.map((c) => (
          <button
            key={c.value}
            type="button"
            onClick={() => setCategory(c.value)}
            className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
              category === c.value ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {items.length === 0 && (
        <p className="card text-sm text-slate-500">No current-affairs items yet — check back after today's refresh.</p>
      )}
      {items.length > 0 && visibleGroups.length === 0 && (
        <p className="card text-sm text-slate-500">Nothing in this view yet.</p>
      )}

      <div className="flex flex-col gap-6">
        {visibleGroups.map(([groupLabel, groupItems]) => (
          <div key={groupLabel} className="flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{groupLabel}</p>
            {groupItems.map((c) => {
              const bookmarked = bookmarkedIds.has(c.id);
              return (
                <Link key={c.id} href={`/current-affairs/${c.id}`} className="card block transition-colors hover:border-brand-200 hover:bg-brand-50/40">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
                      {c.category && <span className="badge">{CATEGORY_LABEL[c.category] ?? c.category}</span>}
                      {c.published_at && <span>{new Date(c.published_at).toLocaleDateString()}</span>}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <button
                        type="button"
                        onClick={(e) => toggleBookmark(c.id, e)}
                        aria-label={bookmarked ? "Remove bookmark" : "Bookmark"}
                        className="rounded p-1 text-slate-400 hover:bg-brand-50 hover:text-brand-600"
                      >
                        <Bookmark className={`h-4 w-4 ${bookmarked ? "fill-brand-600 text-brand-600" : ""}`} />
                      </button>
                      {c.source_url && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            window.open(c.source_url!, "_blank", "noopener,noreferrer");
                          }}
                          className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline"
                        >
                          Source <ArrowUpRight className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="mt-1.5 font-medium text-slate-900">{c.title}</p>
                  <p className="mt-2 line-clamp-3 whitespace-pre-line text-sm leading-relaxed text-slate-600">{c.body}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {c.tags.map((t) => (
                      <span key={t} className="badge">{t}</span>
                    ))}
                  </div>
                </Link>
              );
            })}
          </div>
        ))}
      </div>
    </main>
  );
}
