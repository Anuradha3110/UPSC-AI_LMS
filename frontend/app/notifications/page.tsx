"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { authHeaders } from "@/lib/auth";

type Notification = {
  id: string;
  type: string;
  title: string;
  body: string;
  read: boolean;
  created_at: string;
};

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);

  function load() {
    apiFetch<Notification[]>("/api/v1/notifications", { headers: authHeaders() }).then(setItems).catch(() => {});
  }
  useEffect(load, []);

  async function markRead(id: string) {
    await apiFetch(`/api/v1/notifications/${id}/read`, { method: "POST", headers: authHeaders() });
    load();
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-6 py-10">
      <p className="page-eyebrow">MOD-10 · Notifications</p>
      <h1 className="text-2xl font-semibold text-slate-900">Notifications</h1>

      {items.length === 0 && <p className="card text-sm text-slate-500">Nothing yet.</p>}

      <div className="flex flex-col gap-2">
        {items.map((n) => (
          <button
            key={n.id}
            onClick={() => !n.read && markRead(n.id)}
            className={`rounded-lg border p-3 text-left text-sm transition-colors ${
              n.read ? "border-slate-100 text-slate-500" : "border-brand-200 bg-brand-50/60 hover:bg-brand-50"
            }`}
          >
            <p className="font-medium text-slate-900">{n.title}</p>
            <p className="mt-1">{n.body}</p>
            <p className="mt-1 text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</p>
          </button>
        ))}
      </div>
    </main>
  );
}
