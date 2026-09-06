"use client";

import React, { useRef, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import type { ChatMessage } from "@/store/chatStore";
import { StreamCursor } from "./StreamCursor";
import { CitationChip } from "./CitationChip";
import { ReasoningTrace } from "./ReasoningTrace";
import { cn } from "@/lib/utils";

const heroVariants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } },
};

const heroItem = {
  hidden: { opacity: 0, y: 10, scale: 0.96 },
  show: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { type: "spring", stiffness: 130, damping: 15 },
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
    return (
      <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto p-6 scrollbar-thin">
        <motion.div
          variants={heroVariants}
          initial="hidden"
          animate="show"
          className="w-full max-w-2xl"
        >
          <motion.div variants={heroItem} className="mb-2 flex justify-center">
            <motion.div
              initial={{ opacity: 0, scale: 0.6, rotate: -8 }}
              animate={{ opacity: 1, scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 160, damping: 12 }}
              className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#10a37f] text-lg font-bold text-white shadow-lg shadow-emerald-500/20"
            >
              AE
            </motion.div>
          </motion.div>
          <motion.h1
            variants={heroItem}
            className="text-center text-3xl font-semibold tracking-tight"
          >
            AEGIS-WB
          </motion.h1>
          <motion.p
            variants={heroItem}
            className="mt-2 text-center text-sm text-muted-foreground"
          >
            Sovereign, air-gapped AI for industrial documents. Nothing leaves
            this machine.
          </motion.p>
        </motion.div>
        {suggestions && suggestions.length > 0 && (
          <motion.div
            variants={heroVariants}
            initial="hidden"
            animate="show"
            className="mt-8 grid w-full max-w-2xl grid-cols-1 gap-2 sm:grid-cols-2"
          >
            {suggestions.map((s) => (
              <motion.button
                key={s}
                variants={heroItem}
                whileHover={{ scale: 1.015, y: -1 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onSuggestion?.(s)}
                className="rounded-2xl border border-border bg-card p-4 text-left text-sm text-foreground transition-colors hover:bg-muted/60"
              >
                {s}
              </motion.button>
            ))}
          </motion.div>
        )}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto px-4 py-4 scrollbar-thin"
    >
      <div className="mx-auto max-w-3xl space-y-5">
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
        initial={{ opacity: 0, y: 12, x: 10 }}
        animate={{ opacity: 1, y: 0, x: 0 }}
        transition={{ type: "spring", stiffness: 150, damping: 17 }}
        className="flex justify-end"
      >
        <div className="max-w-[85%] whitespace-pre-wrap rounded-3xl rounded-br-lg border border-border bg-muted/60 px-4 py-2.5 text-[15px] leading-relaxed">
          {msg.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 150, damping: 17 }}
      className="flex flex-col gap-1.5"
    >
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-[#10a37f] text-[9px] font-bold text-white">
          AE
        </div>
        {msg.grounded && (
          <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
            ✓ Grounded in sources
          </span>
        )}
        {msg.abstained && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
            ⚠ Abstained — no sources found
          </span>
        )}
        {msg.intent && (
          <span className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            {msg.intent}
          </span>
        )}
      </div>

      <div className="text-[15px] leading-relaxed">
        <div className="prose prose-sm max-w-none break-words dark:prose-invert">
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
          <span className="text-[11px] text-muted-foreground">Sources:</span>
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

      {msg.sources.length > 0 && (
        <SourcesBlock sources={msg.sources} />
      )}

      {msg.reasoning.length > 0 && <ReasoningTrace steps={msg.reasoning} isStreaming={isStreaming} />}
    </motion.div>
  );
}

function SourcesBlock({
  sources,
}: {
  sources: ChatMessage["sources"];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-0.5 rounded-2xl border border-border bg-card">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3.5 py-2 text-left text-xs font-medium text-muted-foreground"
      >
        <span>{sources.length} pages retrieved ({Math.round(Math.max(...sources.map((s) => s.score)) * 100)}% best match)</span>
        <svg
          className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <ol className="space-y-1 border-t p-2">
          {sources.map((s) => (
            <li
              key={s.n}
              id={`source-${s.n}`}
              className="rounded-lg px-2 py-1.5 text-xs transition-colors hover:bg-muted/50"
            >
              <span className="font-semibold text-foreground">[{s.n}]</span>{" "}
              <span className="text-foreground">{s.document_title}</span>
              <span className="ml-1 text-muted-foreground">
                · p.{s.page_start} · {(s.score * 100).toFixed(0)}% match
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}