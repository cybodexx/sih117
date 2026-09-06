"use client";

import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api-base";

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

interface DocumentTableProps {
  documents: DocRow[];
  onRetry?: (id: string) => void;
}

const STATUS_BADGE: Record<string, string> = {
  QUEUED: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300",
  PROCESSING:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
  READY: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300",
  FAILED: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
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

export function DocumentTable({ documents, onRetry }: DocumentTableProps) {
  if (documents.length === 0) {
    return (
      <div className="rounded-2xl border border-border p-12 text-center">
        <p className="text-sm font-medium text-foreground">No documents yet</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Upload a PDF, image, CSV, or text file above to start indexing.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
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
        <tbody className="divide-y divide-border">
          {documents.map((doc) => {
            const isReady = doc.status === "READY";
            const isFailed = doc.status === "FAILED";
            return (
              <tr key={doc.id} className="transition-colors hover:bg-muted/30">
                <td className="max-w-[260px] px-4 py-2.5">
                  <div className="font-medium text-foreground">{doc.filename}</div>
                  <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                    {doc.mime}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-muted-foreground">
                  {formatBytes(doc.size_bytes)}
                </td>
                <td className="px-4 py-2.5 text-muted-foreground">
                  {doc.page_count ?? "—"}
                </td>
                <td className="px-4 py-2.5 text-muted-foreground">
                  {doc.chunk_count ?? "—"}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                      STATUS_BADGE[doc.status] ||
                        "bg-muted text-muted-foreground"
                    )}
                  >
                    {(doc.status === "PROCESSING" || doc.status === "QUEUED") && (
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                    )}
                    {doc.status === "READY" ? "✓ " : ""}
                    {shortStatus(doc.status)}
                  </span>
                  {isFailed && doc.error_reason && (
                    <div className="mt-1 max-w-[220px] truncate text-[10px] text-destructive" title={doc.error_reason}>
                      {doc.error_reason}
                    </div>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex flex-col gap-1">
                    <span className="w-fit rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {CLEARANCE_LABEL[doc.clearance_level] || "PUBLIC"}
                    </span>
                    <span className="w-fit rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {doc.department}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2.5 text-xs text-muted-foreground">
                  {new Date(doc.created_at).toLocaleString()}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    {isReady && (
                      <a
                        href={`${API_BASE}/api/v1/documents/${doc.id}/file`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs font-medium text-foreground/70 hover:text-foreground"
                      >
                        Open
                      </a>
                    )}
                    {isFailed && onRetry && (
                      <button
                        onClick={() => onRetry(doc.id)}
                        className="rounded-lg bg-foreground px-2.5 py-1 text-[11px] font-semibold text-background hover:opacity-90"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}