"use client";

import Link from "next/link";
import { ChevronsLeft, ChevronsRight, LogOut, X } from "lucide-react";
import type { CurrentUser } from "@/lib/auth";
import { visibleSections } from "@/lib/nav-config";

type Props = {
  pathname: string | null;
  user: CurrentUser | null;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  badgeCounts: Record<string, number>;
  onLogout: () => void;
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export default function Sidebar({
  pathname,
  user,
  collapsed,
  onToggleCollapsed,
  mobileOpen,
  onCloseMobile,
  badgeCounts,
  onLogout,
}: Props) {
  const sections = visibleSections(user?.role);

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-slate-900/40 md:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex flex-col border-r border-slate-200 bg-white transition-all duration-200 ease-in-out ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        } md:translate-x-0 ${collapsed ? "w-[280px] md:w-[76px]" : "w-[280px]"}`}
        aria-label="Primary"
      >
        <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-4 py-4">
          <Link href="/dashboard" className="flex min-w-0 items-center gap-2">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-800 font-mono text-sm font-bold text-white">
              N
            </span>
            <span className={`min-w-0 ${collapsed ? "md:hidden" : ""}`}>
              <span className="block truncate font-mono text-sm font-semibold uppercase tracking-wide text-slate-900">
                Nirdesh
              </span>
              <span className="block truncate text-[11px] text-slate-500">
                UPSC AI Learning Platform
              </span>
            </span>
          </Link>
          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900 md:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Sections">
          {sections.map((section) => (
            <div key={section.label} className="mb-5">
              <p
                className={`mb-1.5 px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 ${
                  collapsed ? "md:hidden" : ""
                }`}
              >
                {section.label}
              </p>
              <ul className="flex flex-col gap-0.5">
                {section.items.map((item) => {
                  const active =
                    pathname === item.href || (pathname?.startsWith(`${item.href}/`) ?? false);
                  const Icon = item.icon;
                  const badge = item.badgeKey ? badgeCounts[item.badgeKey] : undefined;
                  return (
                    <li key={item.href} className="group relative">
                      <Link
                        href={item.href}
                        aria-current={active ? "page" : undefined}
                        title={collapsed ? item.label : undefined}
                        className={`flex items-center gap-3 rounded-lg px-2 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 ${
                          active
                            ? "bg-brand-50 font-medium text-brand-700"
                            : "text-slate-600 hover:bg-brand-50/60 hover:text-slate-900"
                        }`}
                      >
                        <Icon
                          className={`h-[18px] w-[18px] shrink-0 ${
                            active ? "text-brand-600" : "text-slate-400 group-hover:text-slate-600"
                          }`}
                          aria-hidden="true"
                        />
                        <span className={`min-w-0 flex-1 truncate ${collapsed ? "md:hidden" : ""}`}>
                          {item.label}
                        </span>
                        {!!badge && (
                          <span
                            className={`rounded-full bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white ${
                              collapsed ? "md:hidden" : ""
                            }`}
                          >
                            {badge}
                          </span>
                        )}
                      </Link>
                      {collapsed && (
                        <span
                          role="tooltip"
                          className="pointer-events-none absolute left-full top-1/2 z-50 ml-2 hidden -translate-y-1/2 whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-xs text-white shadow-lg md:group-hover:block md:group-focus-within:block"
                        >
                          {item.label}
                          {!!badge && ` (${badge})`}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-slate-100 p-3">
          {user && (
            <div
              className={`flex items-center gap-2 rounded px-1 py-1 ${
                collapsed ? "md:flex-col md:justify-center" : ""
              }`}
            >
              <span
                title={collapsed ? `${user.name} · ${user.role}` : undefined}
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-800 text-xs font-semibold text-white"
              >
                {initials(user.name)}
              </span>
              <span className={`min-w-0 flex-1 ${collapsed ? "md:hidden" : ""}`}>
                <span className="block truncate text-sm font-medium text-slate-900">{user.name}</span>
                <span className="block truncate text-xs capitalize text-slate-500">{user.role}</span>
              </span>
              <button
                type="button"
                onClick={onLogout}
                title="Log out"
                aria-label="Log out"
                className="shrink-0 rounded p-1.5 text-slate-400 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-pressed={collapsed}
            className="mt-2 hidden w-full items-center justify-center gap-2 rounded-lg border border-slate-200 py-1.5 text-xs text-slate-500 hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600 md:flex"
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
            <span className={collapsed ? "md:hidden" : ""}>Collapse</span>
          </button>
        </div>
      </aside>
    </>
  );
}
