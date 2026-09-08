"use client";

import React, { useRef, useEffect, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import type { ChatMessage } from "@/store/chatStore";
import { StreamCursor } from "./StreamCursor";
import { CitationChip } from "./CitationChip";
import { ReasoningTrace } from "./ReasoningTrace";
import { cn } from "@/lib/utils";
import { apiGet, getStoredToken } from "@/lib/api-client";
import { BrandEmblem } from "@/components/BrandEmblem";
import { API_BASE } from "@/lib/api-base";

const EASE = [0.16, 1, 0.3, 1] as const;

const revealLine = (delay: number) => ({
  hidden: { y: "65%" },
  show: {
    y: "0%",
    transition: { duration: 1.0, ease: EASE, delay },
  },
});

const fadeUp = (delay: number) => ({
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.9, ease: EASE, delay },
  },
});

const popIn = {
  hidden: { opacity: 0, scale: 0.9 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.7, ease: EASE, delay: 0.24 },
  },
};

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming: boolean;
  suggestions?: string[];
  onSuggestion?: (s: string) => void;
  onCitationClick?: (n: number) => void;
}

export function MessageList({
  messages,
  isStreaming,
  suggestions,
  onSuggestion,
  onCitationClick,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);

  useEffect(() => {
    const el = containerRef.current;
    function onScroll() {
      if (!el) return;
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      userScrolledRef.current = !atBottom;
    }
    el?.addEventListener("scroll", onScroll, { passive: true });
    return () => el?.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!userScrolledRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  if (messages.length === 0) {
    return <Hero onSuggestion={onSuggestion} />;
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-5 scrollbar-thin"
    >
      <div className="mx-auto max-w-3xl space-y-6">
        {messages.map((msg) => (
          <MessageRow
            key={msg.id}
            msg={msg}
            isStreaming={isStreaming && messages.at(-1)?.id === msg.id}
            onCitationClick={onCitationClick}
          />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function Hero({ onSuggestion }: { onSuggestion?: (s: string) => void }) {
  const [stats, setStats] = useState<{ docs: number; sessions: number } | null>(
    null,
  );

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      apiGet<{ total: number }>("/api/v1/documents?size=1"),
      apiGet<{ total: number }>("/api/v1/chat/sessions?size=1"),
    ]).then(([d, s]) => {
      if (!active) return;
      const docs = d.status === "fulfilled" ? d.value.total : 0;
      const sessions = s.status === "fulfilled" ? s.value.total : 0;
      setStats({ docs, sessions });
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <motion.div
      initial="hidden"
      animate="show"
      className="relative flex flex-1 flex-col justify-center overflow-y-auto px-6 py-10 scrollbar-thin"
    >
      <div className="mx-auto w-full max-w-[820px]">
        {/* Badge */}
        <motion.div variants={popIn} className="mb-7 flex justify-center">
          <span className="metal-pill inline-flex items-center gap-2 rounded-[5px] px-3.5 py-[9px] text-[12.5px] tracking-tight text-gray-200">
            <svg
              className="h-[18px] w-5"
              viewBox="0 0 24 24"
              fill="white"
              style={{ filter: "drop-shadow(0 0 3px rgba(255,255,255,0.45))" }}
            >
              <path d="M12 2.6C12.55 2.6 12.88 3.15 13.08 4.7c.62 4.7 1.52 5.6 6.22 6.22 1.55.2 2.1.53 2.1 1.08s-.55.88-2.1 1.08c-4.7.62-5.6 1.52-6.22 6.22-.2 1.55-.53 2.1-1.08 2.1s-.88-.55-1.08-2.1c-.62-4.7-1.52-5.6-6.22-6.22C3.15 12.88 2.6 12.55 2.6 12s.55-.88 2.1-1.08c4.7-.62 5.6-1.52 6.22-6.22C11.12 3.15 11.45 2.6 12 2.6Z" />
            </svg>
            Sovereign Industrial AI Workbench
          </span>
        </motion.div>

        {/* Headline */}
        <div className="text-center text-[42px] font-medium leading-[1.08] tracking-[-0.04em] text-white md:text-[48px]">
          <span className="block overflow-hidden px-2 pb-[0.14em] pt-[0.06em]">
            <motion.span variants={revealLine(0.5)} className="block">
              Air-gapped AI for your
            </motion.span>
          </span>
          <span className="block overflow-hidden px-2 pb-[0.14em] pt-[0.06em]">
            <motion.span variants={revealLine(0.74)} className="block">
              industrial{" "}
              <em className="serif-accent text-[1.08em] text-white/60">
                workflows.
              </em>
            </motion.span>
          </span>
        </div>

        {/* Lede */}
        <motion.p
          variants={fadeUp(1.0)}
          className="mx-auto mt-[18px] max-w-[470px] text-center text-[15.5px] leading-[1.55] tracking-[-0.015em] text-white/55"
        >
          Adaptive agents that read your document vault and answer only from
          verified sources — nothing ever leaves this machine.
        </motion.p>

        {/* Actions */}
        <motion.div
          variants={fadeUp(1.16)}
          className="mt-7 flex flex-wrap items-center justify-center gap-2.5"
        >
          <button
            onClick={() =>
              onSuggestion?.(
                "Summarise the CSB refinery incident report",
              )
            }
            className="liquid-btn-solid flex h-[42px] cursor-pointer items-center justify-center rounded-[6px] px-5 text-[13.5px] font-medium tracking-tight"
          >
            Ask your documents
          </button>
          <Link
            href="/documents"
            className="btn-glass flex h-[42px] cursor-pointer items-center justify-center rounded-[6px] px-5 text-[13.5px] font-medium tracking-tight"
          >
            Index documents
          </Link>
          <button
            onClick={() => onSuggestion?.("Analyze upload_check.txt")}
            className="btn-glass flex h-[42px] cursor-pointer items-center justify-center rounded-[6px] px-5 text-[13.5px] font-medium tracking-tight"
          >
            Analyze a document
          </button>
        </motion.div>

        {/* Stats */}
        <motion.div
          variants={fadeUp(1.3)}
          className="mt-14 flex items-center justify-center gap-10 text-[13.5px] tracking-[-0.015em] text-[#d8d8d8]"
        >
          <Stat
            icon={
              <>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </>
            }
            label={`${stats ? stats.docs.toLocaleString() : "—"} documents indexed`}
            delay={1.44}
          />
          <span className="h-5 w-px bg-white/15" aria-hidden />
          <Stat
            icon={
              <>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </>
            }
            label={`${stats ? stats.sessions.toLocaleString() : "—"} conversations`}
            delay={1.58}
          />
          <span className="h-5 w-px bg-white/15" aria-hidden />
          <Stat
            icon={
              <>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </>
            }
            label="100% on-premise"
            delay={1.72}
          />
        </motion.div>
      </div>
    </motion.div>
  );
}

function Stat({
  icon,
  label,
  delay,
}: {
  icon: React.ReactNode;
  label: string;
  delay: number;
}) {
  return (
    <motion.span
      variants={{
        hidden: { opacity: 0, y: 20 },
        show: {
          opacity: 1,
          y: 0,
          transition: { duration: 0.9, ease: EASE, delay },
        },
      }}
      className="inline-flex items-center gap-[10px] whitespace-nowrap"
    >
      <svg className="h-5 w-5 text-[#e8e8e8]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        {icon}
      </svg>
      {label}
    </motion.span>
  );
}

function MessageRow({
  msg,
  isStreaming,
  onCitationClick,
}: {
  msg: ChatMessage;
  isStreaming: boolean;
  onCitationClick?: (n: number) => void;
}) {
  if (msg.role === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 14, x: 10 }}
        animate={{ opacity: 1, y: 0, x: 0 }}
        transition={{ type: "spring", stiffness: 140, damping: 18 }}
        className="flex justify-end"
      >
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-[6px] bg-white px-4 py-2.5 text-[15px] leading-relaxed text-black shadow-[0_10px_40px_-14px_rgba(255,255,255,0.4)]">
          {msg.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 140, damping: 18 }}
      className="flex flex-col gap-2"
    >
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2">
          <BrandEmblem size="sm" />
          <span className="text-[13px] font-medium">AEGIS Assistant</span>
        </div>
        {msg.grounded && (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Grounded in sources
          </span>
        )}
        {msg.abstained && (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            No sources found
          </span>
        )}
        {msg.intent && (
          <span className="rounded-full border border-white/15 bg-white/[0.05] px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-white/50">
            {msg.intent}
          </span>
        )}
        {msg.route && (
          <span
            className="inline-flex items-center gap-1 rounded-full border border-sky-400/25 bg-sky-400/10 px-2 py-0.5 text-[10px] font-medium text-sky-300"
            title={`${msg.route.rationale} — this turn used no LLM routing`}
          >
            <svg
              className="h-3 w-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            router · {msg.route.intent} ·{" "}
            {(msg.route.confidence * 100).toFixed(0)}% · {msg.route.tier}
            {msg.route.llm_used ? "" : " · 0 LLM tokens"}
          </span>
        )}
      </div>

      <div className="text-[15px] leading-relaxed">
        <div className="prose prose-sm max-w-none break-words prose-invert prose-headings:text-white prose-p:text-white/85 prose-a:text-white prose-strong:text-white">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {msg.content || ""}
          </ReactMarkdown>
        </div>
        {isStreaming && (
          <span>
            <StreamCursor />
          </span>
        )}
      </div>

      {msg.citations.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] text-white/45">Sources:</span>
          {msg.citations.map((c) => (
            <CitationChip
              key={c.n}
              n={c.n}
              title={c.document_title}
              onClick={() => onCitationClick?.(c.n)}
            />
          ))}
        </div>
      )}

      {msg.sources.length > 0 && <SourcesBlock sources={msg.sources} />}

      {msg.files.length > 0 && <DeliverableCards files={msg.files} />}

      {msg.reasoning.length > 0 && (
        <ReasoningTrace steps={msg.reasoning} isStreaming={isStreaming} />
      )}
    </motion.div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const KIND_LABEL: Record<string, string> = {
  word: "Word document",
  excel: "Excel workbook",
  powerpoint: "PowerPoint deck",
};

function DeliverableCards({
  files,
}: {
  files: ChatMessage["files"];
}) {
  async function download(
    f: ChatMessage["files"][number]
  ) {
    try {
      const token = getStoredToken();
      const res = await fetch(
        `${API_BASE}/api/v1/deliverables/${f.deliverable_id}/file`,
        { headers: token ? { Authorization: `Bearer ${token}` } : undefined }
      );
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = f.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      /* silent */
    }
  }

  return (
    <div className="mt-2 flex flex-col gap-2">
      {files.map((f) => (
        <div
          key={f.deliverable_id}
          className="flex items-center gap-3 rounded-xl border border-white/12 bg-[#0a0a0a] px-3.5 py-2.5"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/12 bg-white/[0.04]">
            <svg
              className="h-4 w-4 text-[#e8e8e8]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-semibold text-white">
              {f.filename}
            </div>
            <div className="text-[10px] text-white/45">
              {KIND_LABEL[f.kind] ?? f.kind} · {formatBytes(f.size_bytes)} ·
              written to the encrypted vault
            </div>
          </div>
          <button
            onClick={() => download(f)}
            className="flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-[11px] font-semibold text-black transition-opacity hover:opacity-90"
          >
            <svg
              className="h-3.5 w-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download
          </button>
        </div>
      ))}
    </div>
  );
}

function SourcesBlock({
  sources,
}: {
  sources: ChatMessage["sources"];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-xl border border-white/12 bg-[#0a0a0a]">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full cursor-pointer items-center justify-between px-3.5 py-2.5 text-left text-xs font-medium text-white/50 transition-colors hover:bg-white/[0.04]"
      >
        <span>
          {sources.length} pages retrieved ·{" "}
          {Math.round(Math.max(...sources.map((s) => s.score)) * 100)}% best
          match
        </span>
        <svg
          className={cn(
            "h-3.5 w-3.5 transition-transform",
            open && "rotate-180",
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      {open && (
        <ol className="space-y-1 border-t border-white/10 p-2">
          {sources.map((s) => (
            <li
              key={s.n}
              id={`source-${s.n}`}
              className="rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-white/[0.05]"
            >
              <span className="font-semibold text-white">[{s.n}]</span>{" "}
              <span className="text-white/80">{s.document_title}</span>
              <span className="ml-1 text-white/40">
                · p.{s.page_start} · {(s.score * 100).toFixed(0)}% match
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}