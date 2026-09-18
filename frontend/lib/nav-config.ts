import {
  LayoutDashboard,
  BookOpen,
  PenLine,
  ListChecks,
  RotateCcw,
  Newspaper,
  Users,
  MessageCircleQuestion,
  Bell,
  CreditCard,
  ClipboardCheck,
  Settings,
  BookmarkCheck,
  type LucideIcon,
} from "lucide-react";
import type { CurrentUser } from "@/lib/auth";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  /** key into the badge counts map passed to the sidebar, e.g. "unread" */
  badgeKey?: string;
};

export type NavSection = {
  label: string;
  /** roles allowed to see this section; omit for all signed-in roles */
  roles?: CurrentUser["role"][];
  items: NavItem[];
};

// Every href below corresponds to a real route under app/. Sections from the
// original design brief that have no backing route (Study Planner, Question
// Bank, AI Tutor, DAF Preparation, Leaderboard, Profile, ...) are omitted
// rather than linked to a page that doesn't exist.
export const NAV_SECTIONS: NavSection[] = [
  {
    label: "Learning",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/syllabus", label: "Syllabus", icon: BookOpen },
      { href: "/practice", label: "Mains Practice", icon: PenLine },
      { href: "/tests/prelims", label: "Prelims Mock", icon: ListChecks },
      { href: "/revision", label: "Revision", icon: RotateCcw },
      { href: "/current-affairs", label: "Current Affairs", icon: Newspaper },
      { href: "/study", label: "My Study Material", icon: BookmarkCheck },
    ],
  },
  {
    label: "Interview",
    items: [{ href: "/interview", label: "Interview Preparation", icon: Users }],
  },
  {
    label: "Community",
    items: [
      { href: "/doubts", label: "Doubts", icon: MessageCircleQuestion },
      { href: "/notifications", label: "Notifications", icon: Bell, badgeKey: "unread" },
    ],
  },
  {
    label: "Account",
    items: [{ href: "/billing", label: "Billing / Subscription", icon: CreditCard }],
  },
  {
    label: "Mentor",
    roles: ["mentor", "admin"],
    items: [{ href: "/mentor", label: "Mentor Queue", icon: ClipboardCheck }],
  },
  {
    label: "Admin",
    roles: ["content_editor", "admin"],
    items: [{ href: "/admin", label: "Content CMS", icon: Settings }],
  },
];

export function visibleSections(role: CurrentUser["role"] | undefined): NavSection[] {
  return NAV_SECTIONS.filter((s) => !s.roles || (role && s.roles.includes(role)));
}

export function getPageTitle(pathname: string | null): string {
  if (!pathname) return "Nirdesh";
  for (const section of NAV_SECTIONS) {
    for (const item of section.items) {
      if (pathname === item.href || pathname.startsWith(`${item.href}/`)) {
        return item.label;
      }
    }
  }
  return "Nirdesh";
}
