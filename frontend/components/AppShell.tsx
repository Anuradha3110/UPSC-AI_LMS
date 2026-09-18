"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api";
import { authHeaders, clearSession, getUser, type CurrentUser } from "@/lib/auth";
import { getPageTitle } from "@/lib/nav-config";
import Sidebar from "./Sidebar";
import TopHeader from "./TopHeader";

const PUBLIC_PATHS = new Set(["/", "/login", "/register"]);
const COLLAPSE_KEY = "nirdesh_sidebar_collapsed";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [unread, setUnread] = useState(0);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setUser(getUser());
  }, [pathname]);

  useEffect(() => {
    const stored = localStorage.getItem(COLLAPSE_KEY);
    if (stored === "1") setCollapsed(true);
  }, []);

  useEffect(() => {
    if (!user) return;
    apiFetch<{ id: string }[]>("/api/v1/notifications?unread_only=true", {
      headers: authHeaders(),
    })
      .then((n) => setUnread(n.length))
      .catch(() => {});
  }, [user, pathname]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setMobileOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      return next;
    });
  }, []);

  function logout() {
    clearSession();
    router.push("/login");
  }

  if (!pathname || PUBLIC_PATHS.has(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-brand-50/50">
      <Sidebar
        pathname={pathname}
        user={user}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        badgeCounts={{ unread }}
        onLogout={logout}
      />
      <div
        className={`flex min-h-screen flex-col transition-[padding] duration-200 ease-in-out ${
          collapsed ? "md:pl-[76px]" : "md:pl-[280px]"
        }`}
      >
        <TopHeader
          title={getPageTitle(pathname)}
          user={user}
          unread={unread}
          onOpenMobile={() => setMobileOpen(true)}
        />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
