"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { useSessionStore } from "@/store/sessionStore";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { BrandEmblem } from "@/components/BrandEmblem";

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
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
  },
  {
    href: "/documents",
    label: "Documents",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    href: "/audit",
    label: "Audit Log",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    href: "/sovereignty",
    label: "Sovereignty",
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
] as const;

function titleFor(path: string) {
  if (path.startsWith("/chat")) return "Chat";
  const map: Record<string, string> = {
    "/documents": "Documents",
    "/audit": "Audit Log",
    "/sovereignty": "Sovereignty",
  };
  return map[path] ?? "AEGIS-WB";
}

export default function WorkbenchLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const token = useSessionStore((s) => s.token);
  const user = useSessionStore((s) => s.user);
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
  const initials = (user?.username ?? "OP").slice(0, 2).toUpperCase();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        router.push("/chat/new");
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router]);

  const pageTitle = useMemo(() => titleFor(pathname), [pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-black text-foreground">
      {/* Sidebar */}
      <motion.aside
        animate={{ width: sidebarOpen ? 264 : 0 }}
        initial={false}
        transition={{ type: "spring", stiffness: 280, damping: 30 }}
        aria-label="Main menu"
        role="navigation"
        className="flex flex-shrink-0 flex-col overflow-hidden border-r border-white/10 bg-[#050505]"
      >
        <div className="flex h-full w-[264px] flex-col">
          {/* Logo */}
          <div className="flex items-center justify-between px-4 py-4">
            <div className="flex items-center gap-2.5">
              <BrandEmblem size="md" />
              <div className="flex min-w-0 flex-col leading-none">
                <span className="text-[15px] font-semibold tracking-tight">
                  AEGIS-WB
                  <span className="ml-0.5 font-normal text-white/60">.ai</span>
                </span>
                <span className="mt-1 text-[10px] uppercase tracking-[0.18em] text-white/40">
                  Sovereign AI
                </span>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="flex h-8 w-8 items-center justify-center rounded-md text-white/40 transition-colors hover:bg-white/5 hover:text-white"
              aria-label="Collapse sidebar"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>
          </div>

          {/* New Chat */}
          <div className="px-3 pb-3">
            <Link
              href="/chat/new"
              className="liquid-btn-solid flex h-10 cursor-pointer items-center justify-center gap-2 rounded-[8px] px-3 text-[13px] font-medium tracking-tight"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New chat
            </Link>
          </div>

          {/* Navigation */}
          <nav className="px-3">
            <div className="space-y-0.5">
              {NAV_ITEMS.map((item) => {
                const active =
                  item.href === "/chat/new" ? isChatActive : pathname === item.href;
                return (
                  <Link
                    key={item.label}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-[8px] px-3 py-2.5 text-[13.5px] transition-all duration-200",
                      active
                        ? "bg-white font-medium text-black shadow-[0_0_20px_rgba(255,255,255,0.22)]"
                        : "text-white/55 hover:bg-white/[0.06] hover:text-white",
                    )}
                  >
                    {item.icon}
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </nav>

          {/* Recent Sessions */}
          <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-white/10 pt-3">
            <div className="px-5 pb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-white/40">
              Recent
            </div>
            <div className="flex-1 overflow-y-auto px-3 pb-2 scrollbar-thin">
              {sessions.length === 0 ? (
                <p className="px-2 py-2 text-xs text-white/40">
                  No conversations yet
                </p>
              ) : (
                sessions.slice(0, 30).map((s) => (
                  <Link
                    key={s.id}
                    href={`/chat/${s.id}`}
                    className={cn(
                      "mt-0.5 flex items-center gap-2 rounded-[8px] px-2.5 py-2 text-[13px] transition-colors",
                      pathname === `/chat/${s.id}`
                        ? "bg-white/10 text-white"
                        : "text-white/50 hover:bg-white/[0.06] hover:text-white",
                    )}
                  >
                    <svg
                      className="h-3.5 w-3.5 flex-shrink-0 opacity-70"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    <span className="truncate">{s.title || "New Chat"}</span>
                  </Link>
                ))
              )}
            </div>

            {/* User / Logout */}
            <div className="flex items-center gap-2.5 border-t border-white/10 px-3 py-3">
              <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-[9px] border border-white/15 bg-white/[0.06] text-[10px] font-bold tracking-tight text-white">
                {initials}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium">
                  {user?.username ?? "Operator"}
                </p>
                <p className="truncate text-[10px] text-white/40">
                  {user?.role ?? "VIEWER"}
                </p>
              </div>
              <button
                onClick={handleLogout}
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-white/40 transition-colors hover:bg-white/10 hover:text-white"
                aria-label="Log out"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </motion.aside>

      {/* Main */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex flex-shrink-0 items-center gap-3 border-b border-white/10 bg-black/60 px-4 py-2.5 backdrop-blur supports-[backdrop-filter]:bg-black/40">
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-white/50 transition-colors hover:bg-white/5 hover:text-white"
              aria-label="Open sidebar"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium tracking-tight leading-tight">
              {pageTitle}
            </p>
            <p className="hidden truncate text-[11px] leading-tight text-white/45 sm:block">
              AEGIS-WB — Operational AI Infrastructure
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full border border-white/15 bg-white/[0.04] px-2.5 py-1 text-[11px] text-white/70 sm:flex">
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-emerald-400"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
              />
              Air-gapped · no egress
            </span>
          </div>
        </header>

        <motion.div
          key={pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
          className="flex-1 overflow-hidden"
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}