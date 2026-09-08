"use client";

import React, { useMemo } from "react";

export interface LayoutBlock {
  class: string;
  confidence: number;
  bbox: number[];
}

export interface LayoutPage {
  page: number;
  blocks: LayoutBlock[];
  model?: string;
}

export interface FileLayout {
  document_id: string;
  document_title: string;
  status: string;
  pages: LayoutPage[];
  summary: { classes: Record<string, number>; block_count: number; page_count: number };
}

export interface SessionLayout {
  session_id: string;
  scope_document_ids: string[];
  files: FileLayout[];
  summary: { classes: Record<string, number>; block_count: number; page_count: number };
}

const CLASS_COLORS: Record<string, string> = {
  title: "bg-emerald-400 text-emerald-950",
  "plain text": "bg-slate-200 text-slate-900",
  text: "bg-slate-200 text-slate-900",
  figure: "bg-violet-400 text-violet-950",
  table: "bg-sky-400 text-sky-950",
  "table caption": "bg-teal-400 text-teal-950",
  "table footnote": "bg-teal-400 text-teal-950",
  "isolate formula": "bg-amber-400 text-amber-950",
  formula: "bg-amber-400 text-amber-950",
  "formula caption": "bg-orange-300 text-orange-950",
  caption: "bg-teal-400 text-teal-950",
  header: "bg-gray-400 text-gray-950",
  footer: "bg-gray-400 text-gray-950",
  abandon: "bg-rose-400 text-rose-950",
};

function classColor(k: string): string {
  const key = k.toLowerCase();
  if (CLASS_COLORS[key]) return CLASS_COLORS[key];
  for (const [prefix, color] of Object.entries(CLASS_COLORS)) {
    if (key.includes(prefix)) return color;
  }
  return "bg-white/15 text-white/80";
}

function SummaryBars({ classes }: { classes: Record<string, number> }) {
  const total = Object.values(classes).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="space-y-1.5">
      {Object.entries(classes)
        .sort((a, b) => b[1] - a[1])
        .map(([k, n]) => (
          <div key={k} className="flex items-center gap-2 text-[11px]">
            <div
              className="h-2 w-20 shrink-0 overflow-hidden rounded-full bg-white/10"
              title={`${k}: ${n}`}
            >
              <div
                className={`h-full rounded-full ${classColor(k)} opacity-80`}
                style={{ width: `${Math.max(4, (n / total) * 100)}%` }}
              />
            </div>
            <span className="w-28 truncate font-medium text-white/70">{k}</span>
            <span className="text-white/50">{n}</span>
          </div>
        ))}
    </div>
  );
}

function PageBlocks({ page }: { page: LayoutPage }) {
  return (
    <div className="space-y-1">
      {page.blocks.length === 0 && (
        <p className="text-[11px] text-white/35">No regions detected on this page.</p>
      )}
      {page.blocks.map((b, i) => (
        <div
          key={`${b.class}-${i}`}
          className="flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.03] px-2 py-1"
        >
          <span
            className={`rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold ${classColor(
              b.class
            )}`}
          >
            {b.class}
          </span>
          <span className="ml-auto font-mono text-[10px] text-white/45">
            {(b.confidence * 100).toFixed(0)}%
          </span>
          <span className="font-mono text-[10px] text-white/25">
            {b.bbox[0].toFixed(2)},{b.bbox[1].toFixed(2)} → {b.bbox[2].toFixed(2)},
            {b.bbox[3].toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function LayoutPanel({
  data,
  loading,
  error,
  onClose,
  onRefresh,
  bare = false,
}: {
  data: SessionLayout | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onRefresh: () => void;
  bare?: boolean;
}) {
  const totalFiles = data?.files?.length ?? 0;
  const analysed = useMemo(
    () => (data?.files ?? []).filter((f) => f.status !== "NOT_ANALYSED").length,
    [data]
  );

  const content = (
    <div className={bare ? "" : "min-h-0 flex-1 overflow-y-auto px-4 py-3"}>
      {loading && (
        <div className="space-y-2">
          <div className="h-3 w-2/3 animate-pulse rounded bg-white/10" />
          <div className="h-3 w-1/2 animate-pulse rounded bg-white/10" />
          <div className="mt-4 h-24 animate-pulse rounded-lg bg-white/[0.05]" />
        </div>
      )}
      {!loading && error && (
        <p className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
          {error}
        </p>
      )}
      {!loading && !error && data && (
        <div className="space-y-4">
          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-white/40">
              Combined across all scoped files
            </h3>
            <SummaryBars classes={data.summary.classes} />
            <p className="mt-2 text-[10px] text-white/40">
              {data.summary.block_count} regions · {data.summary.page_count} pages across{" "}
              {totalFiles} file{totalFiles === 1 ? "" : "s"}
            </p>
          </section>
          {data.files.map((f) => (
            <section key={f.document_id} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
              <div className="mb-2 flex items-center gap-2">
                <span className="truncate text-xs font-medium text-white/85">
                  {f.document_title}
                </span>
                <span
                  className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold ${
                    f.status === "NOT_ANALYSED"
                      ? "bg-white/10 text-white/45"
                      : "bg-emerald-400/20 text-emerald-300"
                  }`}
                >
                  {f.status === "NOT_ANALYSED" ? "no layout" : f.status}
                </span>
              </div>
              {f.summary.block_count > 0 && (
                <p className="mb-2 text-[10px] text-white/40">
                  {f.summary.block_count} regions · {f.summary.page_count} pages
                </p>
              )}
              <div className="space-y-2">
                {f.pages.map((p) => (
                  <details key={p.page} className="open:pb-1">
                    <summary className="cursor-pointer list-none text-[11px] font-medium text-white/70">
                      Page {p.page}
                      <span className="ml-2 text-white/30">({p.blocks.length})</span>
                    </summary>
                    <div className="mt-1.5">
                      <PageBlocks page={p} />
                    </div>
                  </details>
                ))}
                {f.pages.length === 0 && (
                  <p className="text-[11px] text-white/35">
                    No layout stored — layout analysis runs at ingest for PDFs and images.
                  </p>
                )}
              </div>
            </section>
          ))}
        </div>
      )}
      {!loading && !error && !data && (
        <p className="text-[11px] text-white/35">
          Create a scoped chat to inspect how each file is read.
        </p>
      )}
    </div>
  );

  if (bare) return content;

  return (
    <aside className="flex h-full w-[340px] shrink-0 flex-col border-l border-white/10 bg-background-secondary">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h2 className="text-xs font-semibold text-white/90">Document layout</h2>
          <p className="mt-0.5 text-[10px] text-white/40">
            DocLayout-YOLO · {totalFiles} file{totalFiles === 1 ? "" : "s"} scoped ·{" "}
            {analysed}/{totalFiles} analysed
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="rounded-md p-1 text-white/50 hover:bg-white/10 hover:text-white disabled:opacity-40"
            title="Re-fetch layout analysis"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h5M20 20v-5h-5M5.6 9A7 7 0 1112 19a7 7 0 01-6.4-4" />
            </svg>
          </button>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-white/50 hover:bg-white/10 hover:text-white"
            title="Close layout panel"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {content}
    </aside>
  );
}