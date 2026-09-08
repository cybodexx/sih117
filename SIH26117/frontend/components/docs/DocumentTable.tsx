"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api-base";
import { getStoredToken } from "@/lib/api-client";

export type DocStatus = "QUEUED" | "PROCESSING" | "READY" | "FAILED";

export interface DocRow {
  id: string;
  filename: string;
  mime: string;
  size_bytes: number;
  page_count: number | null;
  status: string;
  chunk_count: number | null;
  clearance_level: number;
  department: string;
  error_reason: string | null;
  created_at: string;
  ingested_at: string | null;
}

export interface AnalysisResult {
  report: string;
  chunks_read: number;
  latency_ms: number;
}

export type AnalysisPanel = AnalysisResult | { error: string };

interface DocumentTableProps {
  documents: DocRow[];
  onRetry?: (id: string) => void;
  analyzingId?: string | null;
  analyses?: Record<string, AnalysisPanel>;
  onAnalyze?: (id: string) => void;
  onChat?: (id: string, filename: string) => void;
}

const STATUS_BADGE: Record<string, string> = {
  QUEUED: "bg-white/[0.04] text-white/50",
  PROCESSING: "bg-amber-400/10 text-amber-300",
  READY: "bg-emerald-400/10 text-emerald-300",
  FAILED: "bg-red-500/10 text-red-300",
};

const CLEARANCE_LABEL = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"];

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function shortStatus(s: string) {
  return s.toLowerCase().replace("long", "");
}

function isError(p: AnalysisPanel): p is { error: string } {
  return "error" in p;
}

export function DocumentTable({
  documents,
  onRetry,
  analyzingId,
  analyses,
  onAnalyze,
  onChat,
}: DocumentTableProps) {
  async function openFile(docId: string) {
    try {
      const token = getStoredToken();
      const res = await fetch(
        `${API_BASE}/api/v1/documents/${docId}/file`,
        { headers: token ? { Authorization: `Bearer ${token}` } : undefined }
      );
      if (!res.ok) throw new Error(`Open failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (err) {
      console.error("open file failed", err);
    }
  }
  if (documents.length === 0) {
    return (
      <div className="rounded-2xl border border-white/12 p-12 text-center">
        <p className="text-sm font-medium text-foreground">No documents yet</p>
        <p className="mt-1 text-xs text-white/50">
          Upload a PDF, image, CSV, or text file above to start indexing.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-white/12">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10 bg-white/[0.03] text-left text-[11px] font-semibold uppercase tracking-wide text-white/45">
            <th className="px-4 py-2.5">Document</th>
            <th className="px-4 py-2.5">Size</th>
            <th className="px-4 py-2.5">Pages</th>
            <th className="px-4 py-2.5">Chunks</th>
            <th className="px-4 py-2.5">Status</th>
            <th className="px-4 py-2.5">Labels</th>
            <th className="px-4 py-2.5">Uploaded</th>
            <th className="px-4 py-2.5" />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/10">
          {documents.map((doc) => {
            const isReady = doc.status === "READY";
            const isFailed = doc.status === "FAILED";
            const isAnalyzing = analyzingId === doc.id;
            const panel = analyses?.[doc.id];

            return (
              <React.Fragment key={doc.id}>
                <tr className="transition-colors hover:bg-white/[0.03]">
                  <td className="max-w-[260px] px-4 py-2.5">
                    <div className="font-medium text-foreground">
                      {doc.filename}
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] text-white/45">
                      {doc.mime}
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-white/55">
                    {formatBytes(doc.size_bytes)}
                  </td>
                  <td className="px-4 py-2.5 text-white/55">
                    {doc.page_count ?? "—"}
                  </td>
                  <td className="px-4 py-2.5 text-white/55">
                    {doc.chunk_count ?? "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                        STATUS_BADGE[doc.status] || "bg-white/[0.04] text-white/45"
                      )}
                    >
                      {(doc.status === "PROCESSING" ||
                        doc.status === "QUEUED") && (
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                      )}
                      {doc.status === "READY" && (
                        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      {shortStatus(doc.status)}
                    </span>
                    {isFailed && doc.error_reason && (
                      <div
                        className="mt-1 max-w-[220px] truncate text-[10px] text-red-400"
                        title={doc.error_reason}
                      >
                        {doc.error_reason}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="flex flex-col gap-1">
                      <span className="w-fit rounded bg-white/[0.05] px-1.5 py-0.5 text-[10px] font-medium text-white/55">
                        {CLEARANCE_LABEL[doc.clearance_level] || "PUBLIC"}
                      </span>
                      <span className="w-fit rounded bg-white/[0.05] px-1.5 py-0.5 text-[10px] font-medium text-white/55">
                        {doc.department}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-white/55">
                    {new Date(doc.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {isReady && onAnalyze && (
                        <button
                          onClick={() => onAnalyze(doc.id)}
                          disabled={isAnalyzing}
                          className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/[0.06] px-2.5 py-1 text-[11px] font-medium text-white transition-colors hover:border-white/40 hover:bg-white/10 disabled:opacity-50"
                          title="Run grounded LLM analysis over this document"
                        >
                          {isAnalyzing ? (
                            <>
                              <span className="h-3 w-3 animate-spin rounded-full border border-white/30 border-t-white" />
                              Analyzing…
                            </>
                          ) : (
                            <>
                              <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                              </svg>
                              Analyze
                            </>
                          )}
                        </button>
                      )}
                      {isReady && onChat && (
                        <button
                          onClick={() => onChat(doc.id, doc.filename)}
                          className="flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/[0.06] px-2.5 py-1 text-[11px] font-medium text-white transition-colors hover:border-white/40 hover:bg-white/10"
                          title="Start a chat scoped to this document only"
                        >
                          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72A7.895 7.895 0 013 12V12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                          Chat
                        </button>
                      )}
                      {isReady && (
                        <button
                          onClick={() => openFile(doc.id)}
                          className="text-xs font-medium text-white/70 hover:text-white"
                          title="Open the original file"
                        >
                          Open
                        </button>
                      )}
                      {isFailed && onRetry && (
                        <button
                          onClick={() => onRetry(doc.id)}
                          className="rounded-lg bg-white px-2.5 py-1 text-[11px] font-semibold text-black hover:opacity-90"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
                {isAnalyzing && (
                  <tr>
                    <td colSpan={8} className="bg-black px-4 py-3">
                      <div className="flex items-start gap-2 text-[11px] text-white/60">
                        <span className="mt-0.5 h-2 w-2 shrink-0 animate-pulse rounded-full bg-emerald-400" />
                        <span>
                          Running the local AI on this document — usually takes about a
                          minute. Everything executes on your machine; nothing leaves it.
                        </span>
                      </div>
                    </td>
                  </tr>
                )}
                {panel && (
                  <tr>
                    <td colSpan={8} className="bg-black px-4 py-4">
                      {isError(panel) ? (
                        <div className="flex items-start gap-2 text-sm text-red-300">
                          <svg className="mt-0.5 h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>Analysis failed: {panel.error}</span>
                        </div>
                      ) : (
                        <div className="analysis-card mx-auto max-w-3xl">
                          <div className="mb-3 flex items-center gap-2">
                            <svg
                              className="h-[18px] w-5"
                              viewBox="0 0 24 24"
                              fill="white"
                              style={{ filter: "drop-shadow(0 0 3px rgba(255,255,255,0.45))" }}
                            >
                              <path d="M12 2.6C12.55 2.6 12.88 3.15 13.08 4.7c.62 4.7 1.52 5.6 6.22 6.22 1.55.2 2.1.53 2.1 1.08s-.55.88-2.1 1.08c-4.7.62-5.6 1.52-6.22 6.22-.2 1.55-.53 2.1-1.08 2.1s-.88-.55-1.08-2.1c-.62-4.7-1.52-5.6-6.22-6.22C3.15 12.88 2.6 12.55 2.6 12s.55-.88 2.1-1.08c4.7-.62 5.6-1.52 6.22-6.22C11.12 3.15 11.45 2.6 12 2.6Z" />
                            </svg>
                            <span className="text-sm font-semibold tracking-tight">
                              AI Analysis
                            </span>
                            <span className="ml-auto text-[11px] text-white/45">
                              {panel.chunks_read} chunks ·{" "}
                              {(panel.latency_ms / 1000).toFixed(1)}s · grounded
                              on sources
                            </span>
                          </div>
                          <div className="prose prose-sm max-w-none break-words prose-invert prose-headings:text-white prose-headings:mx-0 prose-p:text-white/85 prose-li:text-white/85 prose-strong:text-white prose-td:text-white/85 prose-table:text-[13px]">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {panel.report}
                            </ReactMarkdown>
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}