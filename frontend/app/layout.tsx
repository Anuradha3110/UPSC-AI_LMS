import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/AppShell";

export const metadata: Metadata = {
  title: "Nirdesh — UPSC Prep",
  description: "AI-native preparation platform for the UPSC Civil Services Examination",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-brand-50/40 text-slate-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
