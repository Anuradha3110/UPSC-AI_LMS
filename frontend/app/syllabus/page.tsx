"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type Node = {
  id: string;
  paper: string;
  title: string;
  parent_id: string | null;
  tags: string[];
  optional_subject: string | null;
};

type ContentItem = {
  id: string;
  title: string;
  body: string;
  source_type: string;
  source_url: string | null;
};

const PAPERS = ["GS1", "GS2", "GS3", "GS4", "CSAT", "ESSAY", "OPTIONAL"];

export default function SyllabusPage() {
  const [paper, setPaper] = useState("GS1");
  const [subjects, setSubjects] = useState<string[]>([]);
  const [optionalSubject, setOptionalSubject] = useState("");
  const [nodes, setNodes] = useState<Node[]>([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [content, setContent] = useState<ContentItem[]>([]);

  useEffect(() => {
    apiFetch<string[]>("/api/v1/syllabus/optional-subjects").then(setSubjects).catch(() => {});
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({ paper });
    if (paper === "OPTIONAL" && optionalSubject) params.set("optional_subject", optionalSubject);
    apiFetch<Node[]>(`/api/v1/syllabus?${params}`)
      .then(setNodes)
      .catch(() => setNodes([]));
    setSelectedNode(null);
    setContent([]);
  }, [paper, optionalSubject]);

  useEffect(() => {
    if (!selectedNode) return;
    apiFetch<ContentItem[]>(`/api/v1/content?syllabus_node_id=${selectedNode.id}`)
      .then(setContent)
      .catch(() => setContent([]));
  }, [selectedNode]);

  const tree = useMemo(() => {
    const roots = nodes.filter((n) => !n.parent_id);
    const childrenOf = (id: string) => nodes.filter((n) => n.parent_id === id);
    return { roots, childrenOf };
  }, [nodes]);

  function NodeBranch({ node, depth }: { node: Node; depth: number }) {
    const children = tree.childrenOf(node.id);
    return (
      <div>
        <button
          onClick={() => setSelectedNode(node)}
          className={`block w-full rounded-lg px-2 py-1.5 text-left text-sm ${depth === 0 ? "font-medium" : "text-slate-600"} ${
            selectedNode?.id === node.id ? "bg-brand-600 text-white" : "hover:bg-brand-50"
          }`}
        >
          {node.title}
        </button>
        {children.length > 0 && (
          <div className="ml-3 border-l border-slate-200 pl-2">
            {children.map((child) => (
              <NodeBranch key={child.id} node={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-02 · Syllabus Graph</p>
      <h1 className="text-2xl font-semibold text-slate-900">Syllabus &amp; Reading Material</h1>

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

      {paper === "OPTIONAL" && (
        <select
          value={optionalSubject}
          onChange={(e) => setOptionalSubject(e.target.value)}
          className="input w-fit"
        >
          <option value="">All optional subjects</option>
          {subjects.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      )}

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <div className="flex flex-col gap-1">
          {nodes.length === 0 && <p className="text-sm text-slate-500">No nodes seeded for this paper yet.</p>}
          {tree.roots.map((root) => (
            <NodeBranch key={root.id} node={root} depth={0} />
          ))}
        </div>

        <div className="card">
          {!selectedNode && <p className="text-sm text-slate-500">Select a topic to see reading material.</p>}
          {selectedNode && (
            <>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-medium uppercase text-slate-500">{selectedNode.tags.join(", ")}</p>
                  <h2 className="mt-1 text-lg font-semibold text-slate-900">{selectedNode.title}</h2>
                </div>
                <button
                  onClick={() =>
                    apiFetch(`/api/v1/revision/${selectedNode.id}/review`, {
                      method: "POST",
                      headers: authHeaders(),
                      body: JSON.stringify({ quality: 3 }),
                    }).then(() => alert("Added to your revision queue."))
                  }
                  className="btn-secondary shrink-0 !px-2.5 !py-1 text-xs"
                >
                  Add to revision queue
                </button>
              </div>
              {content.length === 0 && (
                <p className="mt-3 text-sm text-slate-500">No reading material tagged to this node yet.</p>
              )}
              <div className="mt-3 flex flex-col gap-4">
                {content.map((c) => (
                  <div key={c.id} className="border-t border-slate-100 pt-3 first:border-0 first:pt-0">
                    <p className="text-sm font-medium text-slate-900">{c.title}</p>
                    <p className="mt-1 text-xs uppercase text-slate-400">{c.source_type.replace(/_/g, " ")}</p>
                    <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700">{c.body}</p>
                    {c.source_url && (
                      <a href={c.source_url} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-brand-600 underline">
                        Source
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
