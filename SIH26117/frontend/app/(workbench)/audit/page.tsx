"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";

interface AuditRow {
  id: string;
  ts: string;
  user_id: string | null;
  role: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  correlation_id: string | null;
  decision: string | null;
  severity: string | null;
}

interface VerifyResult {
  valid: boolean;
  entries: number;
  first_break: number | null;
  anchor: string;
}

const SEVERITY_STYLE: Record<string, string> = {
  info: "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300",
  error: "bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300",
};

export default function AuditPage() {
  const [rows, setRows] = useState<AuditRow[]>([]);
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchAudit = useCallback(async () => {
    try {
      const data = await apiGet<{ items: AuditRow[]; total: number }>(
        "/api/v1/audit?size=100"
      );
      setRows(data.items || []);
      setError(false);

      const v = await apiGet<VerifyResult>("/api/v1/audit/verify");
      setVerify(v);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAudit();
    const interval = setInterval(fetchAudit, 8000);
    return () => clearInterval(interval);
  }, [fetchAudit]);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-sm text-muted-foreground">Loading audit chain…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-border p-6 text-center">
          <h2 className="text-sm font-semibold">Cannot read audit log</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            The audit log requires an Auditor or Admin role. Log in with a
            privileged account and try again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="mx-auto max-w-6xl space-y-6 p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Audit Log</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Append-only, hash-chained event trail.
            </p>
          </div>
          {verify && (
            <div
              className={cn(
                "rounded-2xl border px-4 py-3 text-sm",
                verify.valid
                  ? "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/40"
                  : "border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40"
              )}
            >
              <div className="flex items-center gap-2 font-semibold">
                <span
                  className={cn(
                    "inline-block h-2.5 w-2.5 rounded-full",
                    verify.valid ? "bg-emerald-500" : "bg-red-500"
                  )}
                />
                {verify.valid ? "Chain verified — intact" : "CHAIN BROKEN"}
              </div>
              <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                {verify.entries} entries · anchor sha256:
                {verify.anchor.slice(0, 24)}…
              </div>
            </div>
          )}
        </div>

        {rows.length === 0 ? (
          <div className="rounded-2xl border border-border p-12 text-center text-sm text-muted-foreground">
            No audit events recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-2xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-2.5">Time</th>
                  <th className="px-4 py-2.5">Action</th>
                  <th className="px-4 py-2.5">Severity</th>
                  <th className="px-4 py-2.5">User</th>
                  <th className="px-4 py-2.5">Role</th>
                  <th className="px-4 py-2.5">Resource</th>
                  <th className="px-4 py-2.5">Correlation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {rows.map((row) => (
                  <tr key={row.id} className="transition-colors hover:bg-muted/30">
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-[11px] text-muted-foreground">
                      {new Date(row.ts).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="font-mono text-[11px] font-medium">
                        {row.action}
                      </span>
                      {row.decision && (
                        <div className="max-w-[200px] truncate text-[10px] text-muted-foreground">
                          {row.decision}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase",
                          SEVERITY_STYLE[row.severity || ""] ||
                            "bg-muted text-muted-foreground"
                        )}
                      >
                        {row.severity || "info"}
                      </span>
                    </td>
                    <td className="max-w-[140px] truncate px-4 py-2.5 font-mono text-[11px]">
                      {row.user_id ? row.user_id.slice(0, 8) : "—"}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {row.role || "—"}
                    </td>
                    <td className="max-w-[180px] px-4 py-2.5">
                      <div className="truncate text-xs text-muted-foreground">
                        {row.resource_type || "—"}
                      </div>
                      {row.resource_id && (
                        <div className="truncate font-mono text-[10px] text-muted-foreground">
                          {row.resource_id}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-[10px] text-muted-foreground">
                      {row.correlation_id ? row.correlation_id.slice(0, 8) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}