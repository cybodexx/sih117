"use client";

import { useCallback, useEffect, useState } from "react";
import { Dropzone } from "@/components/docs/Dropzone";
import { DocumentTable, type DocRow } from "@/components/docs/DocumentTable";
import { useUpload } from "@/hooks/useUpload";
import { apiGet, apiPost } from "@/lib/api-client";

interface QueueItem {
  name: string;
  status: "uploading" | "done" | "error";
  detail?: string;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocRow[]>([]);
  const { upload } = useUpload();
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [refreshing, setRefreshing] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const data = await apiGet<{ items: DocRow[]; total: number }>(
        "/api/v1/documents?size=100"
      );
      setDocs(data.items || []);
      setRefreshing(false);
    } catch {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 3000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  async function handleFiles(files: File[]) {
    for (const file of files) {
      setQueue((q) => [...q, { name: file.name, status: "uploading" }]);
      const id = await upload(file);
      setQueue((q) =>
        q.map((item) =>
          item.name === file.name
            ? id
              ? { name: item.name, status: "done" }
              : { name: item.name, status: "error", detail: "Upload failed" }
            : item
        )
      );
    }
    setTimeout(() => {
      setQueue((q) => q.filter((item) => item.status !== "uploading"));
      fetchAll();
    }, 400);
  }

  async function handleRetry(documentId: string) {
    try {
      await apiPost(`/api/v1/documents/${documentId}/retry`, {});
      fetchAll();
    } catch {
      // ignore
    }
  }

  function clearErrors() {
    setQueue((q) => q.filter((item) => item.status !== "error"));
  }

  const activeJobs = docs.filter(
    (d) => d.status === "QUEUED" || d.status === "PROCESSING"
  );

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Upload files to the sovereign vault. They are parsed, chunked, and
            embedded locally — nothing leaves this machine.
          </p>
        </div>

        <Dropzone onFiles={handleFiles} />

        {queue.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Upload queue
            </div>
            {queue.map((item, i) => (
              <div
                key={`${item.name}-${i}`}
                className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-sm"
              >
                {item.status === "uploading" && (
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-muted-foreground/30 border-t-muted-foreground" />
                )}
                {item.status === "done" && (
                  <span className="text-emerald-500">✓</span>
                )}
                {item.status === "error" && (
                  <span className="text-destructive">✕</span>
                )}
                <span className="truncate">{item.name}</span>
                <span className="ml-auto text-xs text-muted-foreground">
                  {item.status === "uploading"
                    ? "Uploading…"
                    : item.status === "done"
                    ? "Queued for ingestion"
                    : item.detail}
                </span>
              </div>
            ))}
          </div>
        )}

        {(activeJobs.length > 0 || refreshing) && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
            {refreshing
              ? "Loading vault…"
              : `${activeJobs.length} document(s) being indexed — status refreshes automatically`}
          </div>
        )}

        <DocumentTable documents={docs} onRetry={handleRetry} />

        {queue.some((q) => q.status === "error") && (
          <button
            onClick={clearErrors}
            className="text-xs text-muted-foreground underline-offset-2 hover:underline"
          >
            Dismiss upload errors
          </button>
        )}
      </div>
    </div>
  );
}