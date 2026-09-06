"use client";

import React, { useEffect, useRef, useCallback, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { apiGet } from "@/lib/api-client";

interface ChatSession {
  id: string;
  title: string;
  updated_at: string;
}

interface ChatShellProps {
  children: React.ReactNode;
}

export function ChatShell({ children }: ChatShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  const fetchSessions = useCallback(async () => {
    try {
      const data = await apiGet<ChatSession[]>("/api/v1/chat/sessions");
      setSessions(data);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

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

  return (
    <div className="flex h-full">
      {!collapsed && (
        <aside className="flex w-64 flex-shrink-0 flex-col border-r bg-muted/30">
          <div className="flex items-center justify-between border-b px-3 py-2.5">
            <span className="text-xs font-semibold uppercase text-muted-foreground">
              Chats
            </span>
            <button
              onClick={() => setCollapsed(true)}
              className="text-muted-foreground hover:text-foreground"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>
          </div>
          <div className="p-2">
            <Link
              href="/chat/new"
              className="flex w-full items-center gap-2 rounded-md border border-dashed px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            >
              + New Chat
            </Link>
          </div>
          <nav className="flex-1 overflow-y-auto px-2 pb-2 scrollbar-thin">
            {sessions.map((s) => (
              <Link
                key={s.id}
                href={`/chat/${s.id}`}
                className={cn(
                  "block truncate rounded-md px-2 py-1.5 text-sm transition-colors",
                  pathname === `/chat/${s.id}`
                    ? "bg-accent text-accent-foreground font-medium"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                {s.title || "New Chat"}
              </Link>
            ))}
          </nav>
          <div className="border-t px-3 py-2">
            <span className="text-[10px] text-muted-foreground">⌘K new chat</span>
          </div>
        </aside>
      )}
      <div className="flex flex-1 flex-col overflow-hidden">{children}</div>
    </div>
  );
}
