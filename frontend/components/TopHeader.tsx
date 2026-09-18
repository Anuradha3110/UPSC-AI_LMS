"use client";

import Link from "next/link";
import { Bell, Menu } from "lucide-react";
import type { CurrentUser } from "@/lib/auth";

type Props = {
  title: string;
  user: CurrentUser | null;
  unread: number;
  onOpenMobile: () => void;
};

export default function TopHeader({ title, user, unread, onOpenMobile }: Props) {
  return (
    <header className="sticky top-0 z-20 flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobile}
          className="rounded-lg p-1.5 text-slate-500 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600 md:hidden"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
        <h1 className="truncate text-sm font-semibold text-slate-900 sm:text-base">{title}</h1>
      </div>

      {user && (
        <div className="flex shrink-0 items-center gap-3">
          <Link
            href="/notifications"
            className="relative rounded-lg p-1.5 text-slate-500 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
            aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
          >
            <Bell className="h-5 w-5" />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
                {unread}
              </span>
            )}
          </Link>
          <span className="hidden text-sm text-slate-600 sm:inline">
            {user.name} <span className="text-slate-400">· {user.role}</span>
          </span>
        </div>
      )}
    </header>
  );
}
