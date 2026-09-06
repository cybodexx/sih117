"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { useSessionStore } from "@/store/sessionStore";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface PageRead<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

const NAV_ITEMS = [
  {
    href: "/chat/new",
    label: "Chat",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    href: "/documents",
    label: "Documents",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    href: "/audit",
    label: "Audit Log",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    href: "/sovereignty",
    label: "Sovereignty",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 6l9-4 9 4m-9 14V6m-8 4v6a2 2 0 002 2h12a2 2 0 002-2v-6" />
      </svg>
    ),
  },
];

export default function WorkbenchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const token = useSessionStore((s) => s.token);
  const logout = useSessionStore((s) => s.logout);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [token, router]);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiGet<PageRead<ChatSession>>("/api/v1/chat/sessions");
      setSessions(data.items || []);
    } catch {
      // silent — sidebar stays empty
    }
  }, []);

  useEffect(() => {
    if (token) fetchSessions();
  }, [token, fetchSessions, pathname]);

  function handleLogout() {
    logout();
    router.replace("/login");
  }

  const isChatActive = pathname.startsWith("/chat") || pathname === "/";

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      {/* Sidebar */}
      <aside
        className={cn(
          "flex flex-shrink-0 flex-col bg-sidebar text-sidebar-foreground transition-all duration-200",
          sidebarOpen ? "w-[260px]" : "w-0"
        )}
      >
        <div className="flex items-center justify-between px-4 py-3.5">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#10a37f] text-[11px] font-bold text-white">
              AE
            </div>
            {sidebarOpen && (
              <span className="text-sm font-semibold tracking-tight">AEGIS-WB</span>
            )}
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className={cn(
              "text-sidebar-muted hover:text-sidebar-foreground",
              !sidebarOpen && "hidden"
            )}
            aria-label="Collapse sidebar"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>

        <div className="px-3 pb-2">
          <Link
            href="/chat/new"
            className="flex items-center justify-center gap-2 rounded-lg border border-sidebar-border bg-sidebar-muted/10 px-3 py-2.5 text-sm font-medium text-sidebar-foreground transition-colors hover:border-sidebar-muted hover:bg-sidebar-muted/20"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span>New chat</span>
          </Link>
        </div>

        <nav className="px-3 pt-2">
          <div className="space-y-0.5">
            {NAV_ITEMS.map((item) => {
              const active =
                item.href === "/chat/new" ? isChatActive : pathname === item.href;
              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                    active
                      ? "bg-sidebar-muted/20 text-sidebar-foreground"
                      : "text-sidebar-muted hover:bg-sidebar-muted/10 hover:text-sidebar-foreground"
                  )}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>

        <div className="mt-4 flex-1 overflow-y-auto border-t border-sidebar-border px-3 pt-3 scrollbar-thin">
          <div className="px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-sidebar-muted">
            Recent
          </div>
          {sessions.length === 0 ? (
            <p className="px-2 py-1 text-xs text-sidebar-muted">
              No conversations yet
            </p>
          ) : (
            sessions.slice(0, 30).map((s) => (
              <Link
                key={s.id}
                href={`/chat/${s.id}`}
                className={cn(
                  "mt-0.5 flex items-center gap-2 rounded-lg px-2 py-2 text-sm transition-colors",
                  pathname === `/chat/${s.id}`
                    ? "bg-sidebar-muted/20 text-sidebar-foreground"
                    : "text-sidebar-muted hover:bg-sidebar-muted/10 hover:text-sidebar-foreground"
                )}
              >
                <svg className="h-3.5 w-3.5 flex-shrink-0 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="truncate">{s.title || "New Chat"}</span>
              </Link>
            ))
          )}
        </div>

        <div className="border-t border-sidebar-border p-3">
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-sidebar-muted transition-colors hover:bg-sidebar-muted/10 hover:text-sidebar-foreground"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Log out</span>
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-shrink-0 items-center gap-2 border-b border-border bg-background/80 px-4 py-2 backdrop-blur">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Open sidebar"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
          <div className="flex items-center gap-2">
            <span className="hidden text-sm font-medium text-muted-foreground sm:block md:hidden lg:block">
              {pathname === "/chat/new" || pathname.startsWith("/chat")
                ? "AEGIS-WB — Sovereign Industrial AI Workbench"
                : pathname === "/documents"
                ? "Documents"
                : pathname === "/audit"
                ? "Audit Log"
                : pathname === "/sovereignty"
                ? "Sovereignty"
                : "AEGIS-WB"}
            </span>
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground sm:flex">
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              />
              Air-gapped
            </span>
            <ThemeToggle />
          </div>
        </header>

        <motion.div
          key={pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18, ease: "easeOut" }}
          className="flex-1 overflow-hidden"
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}