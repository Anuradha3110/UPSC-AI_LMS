"use client";

import { useMemo, useRef, useState } from "react";
import { Copy, Highlighter, StickyNote, Trash2, X } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

export type HighlightColor = "yellow" | "green" | "blue" | "pink";

export type Annotation = {
  id: string;
  content_item_id: string;
  color: HighlightColor;
  selected_text: string;
  start_offset: number;
  end_offset: number;
  note_text: string | null;
};

const COLOR_LABEL: Record<HighlightColor, string> = {
  yellow: "Important",
  green: "Key Fact",
  blue: "Concept",
  pink: "Revision",
};

const COLOR_MARK_CLASS: Record<HighlightColor, string> = {
  yellow: "bg-yellow-200/70 decoration-yellow-500",
  green: "bg-green-200/70 decoration-green-500",
  blue: "bg-blue-200/70 decoration-blue-500",
  pink: "bg-pink-200/70 decoration-pink-500",
};

const COLOR_DOT_CLASS: Record<HighlightColor, string> = {
  yellow: "bg-yellow-400",
  green: "bg-green-500",
  blue: "bg-blue-500",
  pink: "bg-pink-500",
};

const COLORS: HighlightColor[] = ["yellow", "green", "blue", "pink"];

type SelectionMenu = {
  x: number;
  y: number;
  start: number;
  end: number;
  text: string;
  mode: "menu" | "color" | "note";
};

type OpenAnnotation = {
  x: number;
  y: number;
  annotation: Annotation;
  editing: boolean;
  draft: string;
};

function offsetAt(container: Node, node: Node, offset: number): number {
  const pre = document.createRange();
  pre.selectNodeContents(container);
  pre.setEnd(node, offset);
  return pre.toString().length;
}

type Segment = { text: string; annotation?: Annotation };

function buildSegments(text: string, annotations: Annotation[]): Segment[] {
  const sorted = [...annotations]
    .filter((a) => a.start_offset >= 0 && a.end_offset <= text.length && a.end_offset > a.start_offset)
    .sort((a, b) => a.start_offset - b.start_offset);

  const segments: Segment[] = [];
  let cursor = 0;
  for (const ann of sorted) {
    if (ann.start_offset < cursor) continue; // overlapping highlight — skip rendering it, data stays intact
    if (ann.start_offset > cursor) segments.push({ text: text.slice(cursor, ann.start_offset) });
    segments.push({ text: text.slice(ann.start_offset, ann.end_offset), annotation: ann });
    cursor = ann.end_offset;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor) });
  return segments;
}

export default function HighlightableText({
  contentItemId,
  text,
  annotations,
  onAnnotationsChange,
}: {
  contentItemId: string;
  text: string;
  annotations: Annotation[];
  onAnnotationsChange: (next: Annotation[]) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [menu, setMenu] = useState<SelectionMenu | null>(null);
  const [open, setOpen] = useState<OpenAnnotation | null>(null);
  const [noteDraft, setNoteDraft] = useState("");

  const segments = useMemo(() => buildSegments(text, annotations), [text, annotations]);

  function handleMouseUp() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return;
    const range = sel.getRangeAt(0);
    const container = containerRef.current;
    if (!container || !container.contains(range.commonAncestorContainer)) return;

    const start = offsetAt(container, range.startContainer, range.startOffset);
    const end = offsetAt(container, range.endContainer, range.endOffset);
    if (end <= start) return;

    const rect = range.getBoundingClientRect();
    setOpen(null);
    setNoteDraft("");
    setMenu({
      x: rect.left + rect.width / 2 + window.scrollX,
      y: rect.top + window.scrollY,
      start,
      end,
      text: text.slice(start, end),
      mode: "menu",
    });
  }

  async function commitHighlight(color: HighlightColor, note: string | null) {
    if (!menu) return;
    const created = await apiFetch<Annotation>("/api/v1/study/annotations", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        content_item_id: contentItemId,
        color,
        selected_text: menu.text,
        start_offset: menu.start,
        end_offset: menu.end,
        note_text: note,
      }),
    });
    onAnnotationsChange([...annotations, created]);
    setMenu(null);
    window.getSelection()?.removeAllRanges();
  }

  async function copySelection() {
    if (!menu) return;
    try {
      await navigator.clipboard.writeText(menu.text);
    } catch {
      // clipboard permission denied — nothing else we can do here
    }
    setMenu(null);
    window.getSelection()?.removeAllRanges();
  }

  async function deleteAnnotation(id: string) {
    await apiFetch(`/api/v1/study/annotations/${id}`, { method: "DELETE", headers: authHeaders() });
    onAnnotationsChange(annotations.filter((a) => a.id !== id));
    setOpen(null);
  }

  async function saveNoteEdit(id: string, noteText: string) {
    const updated = await apiFetch<Annotation>(`/api/v1/study/annotations/${id}`, {
      method: "PATCH",
      headers: authHeaders(),
      body: JSON.stringify({ note_text: noteText }),
    });
    onAnnotationsChange(annotations.map((a) => (a.id === id ? updated : a)));
    setOpen(null);
  }

  return (
    <div className="relative">
      <div
        ref={containerRef}
        onMouseUp={handleMouseUp}
        className="whitespace-pre-line font-serif text-[16px] leading-[1.8] text-slate-800"
      >
        {segments.map((seg, i) =>
          seg.annotation ? (
            <mark
              key={i}
              className={`cursor-pointer rounded-[2px] px-0.5 ${COLOR_MARK_CLASS[seg.annotation.color]}`}
              onClick={(e) => {
                const rect = (e.target as HTMLElement).getBoundingClientRect();
                setMenu(null);
                setNoteDraft(seg.annotation!.note_text ?? "");
                setOpen({
                  x: rect.left + rect.width / 2 + window.scrollX,
                  y: rect.top + window.scrollY,
                  annotation: seg.annotation!,
                  editing: false,
                  draft: seg.annotation!.note_text ?? "",
                });
              }}
            >
              {seg.text}
              {seg.annotation.note_text && (
                <StickyNote className="ml-0.5 inline h-3 w-3 text-slate-600" aria-hidden="true" />
              )}
            </mark>
          ) : (
            <span key={i}>{seg.text}</span>
          )
        )}
      </div>

      {menu && (
        <div
          className="fixed z-50 -translate-x-1/2 -translate-y-full rounded-lg border border-slate-200 bg-white p-1.5 shadow-lg"
          style={{ left: menu.x, top: menu.y - 8 }}
        >
          {menu.mode === "menu" && (
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setMenu({ ...menu, mode: "color" })}
                className="flex items-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-brand-50"
              >
                <Highlighter className="h-3.5 w-3.5" /> Highlight
              </button>
              <button
                type="button"
                onClick={() => setMenu({ ...menu, mode: "note" })}
                className="flex items-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-brand-50"
              >
                <StickyNote className="h-3.5 w-3.5" /> Add Note
              </button>
              <button
                type="button"
                onClick={copySelection}
                className="flex items-center gap-1.5 rounded px-2 py-1.5 text-xs font-medium text-slate-700 hover:bg-brand-50"
              >
                <Copy className="h-3.5 w-3.5" /> Copy
              </button>
              <button
                type="button"
                onClick={() => setMenu(null)}
                className="rounded p-1.5 text-slate-400 hover:bg-slate-100"
                aria-label="Close"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )}

          {menu.mode === "color" && (
            <div className="flex items-center gap-1.5 px-1 py-1">
              {COLORS.map((c) => (
                <button
                  key={c}
                  type="button"
                  title={COLOR_LABEL[c]}
                  onClick={() => commitHighlight(c, null)}
                  className={`h-6 w-6 rounded-full ${COLOR_DOT_CLASS[c]} ring-2 ring-transparent transition hover:ring-slate-300`}
                />
              ))}
            </div>
          )}

          {menu.mode === "note" && (
            <div className="flex w-64 flex-col gap-2 p-1.5">
              <textarea
                autoFocus
                value={noteDraft}
                onChange={(e) => setNoteDraft(e.target.value)}
                placeholder="Your note…"
                rows={3}
                className="input !py-1.5 text-xs"
              />
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1">
                  {COLORS.map((c) => (
                    <button
                      key={c}
                      type="button"
                      title={COLOR_LABEL[c]}
                      onClick={() => commitHighlight(c, noteDraft.trim() || null)}
                      className={`h-5 w-5 rounded-full ${COLOR_DOT_CLASS[c]} ring-2 ring-transparent transition hover:ring-slate-300`}
                    />
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setMenu(null)}
                  className="text-xs font-medium text-slate-400 hover:text-slate-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {open && (
        <div
          className="fixed z-50 -translate-x-1/2 rounded-lg border border-slate-200 bg-white p-3 shadow-lg"
          style={{ left: open.x, top: open.y + 20 }}
        >
          <div className="flex w-64 flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className={`badge`}>{COLOR_LABEL[open.annotation.color]}</span>
              <button
                type="button"
                onClick={() => setOpen(null)}
                className="rounded p-1 text-slate-400 hover:bg-slate-100"
                aria-label="Close"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <p className="text-xs italic text-slate-500">&ldquo;{open.annotation.selected_text}&rdquo;</p>
            {open.editing ? (
              <textarea
                autoFocus
                value={noteDraft}
                onChange={(e) => setNoteDraft(e.target.value)}
                rows={3}
                className="input !py-1.5 text-xs"
              />
            ) : (
              open.annotation.note_text && (
                <p className="rounded-md bg-brand-50 p-2 text-xs text-slate-700">{open.annotation.note_text}</p>
              )
            )}
            <div className="flex items-center justify-between gap-2">
              {open.editing ? (
                <button
                  type="button"
                  onClick={() => saveNoteEdit(open.annotation.id, noteDraft)}
                  className="text-xs font-medium text-brand-600 hover:underline"
                >
                  Save note
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setOpen({ ...open, editing: true })}
                  className="text-xs font-medium text-brand-600 hover:underline"
                >
                  {open.annotation.note_text ? "Edit note" : "Add note"}
                </button>
              )}
              <button
                type="button"
                onClick={() => deleteAnnotation(open.annotation.id)}
                className="flex items-center gap-1 text-xs font-medium text-red-600 hover:underline"
              >
                <Trash2 className="h-3.5 w-3.5" /> Remove highlight
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
