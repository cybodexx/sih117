"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";

interface ModelInfo {
  role: string;
  name: string;
  digest: string;
  source: string;
}

interface SovereigntyStatus {
  airgap_mode: boolean;
  network_mode: string;
  dns_resolvable: boolean;
  attempts: number;
  blocked: number;
  reached: number;
  bytes_egressed: number;
  uptime_s: number;
  last_probe_at: string | null;
  models: ModelInfo[];
  breach: string | null;
}

export function ProofPanel() {
  const [status, setStatus] = useState<SovereigntyStatus | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    async function poll() {
      try {
        const data = await apiGet<SovereigntyStatus>("/api/v1/sovereignty/status");
        if (active) {
          setStatus(data);
          setError(false);
        }
      } catch {
        if (active) setError(true);
      }
    }
    poll();
    const interval = setInterval(poll, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  if (error && !status) {
    return (
      <div className="rounded-lg border p-4 text-center text-sm text-destructive">
        Could not reach sovereignty endpoint.
      </div>
    );
  }

  if (!status) {
    return (
      <div className="animate-pulse rounded-lg border p-4">
        <div className="h-4 w-48 rounded bg-muted" />
        <div className="mt-3 h-3 w-32 rounded bg-muted" />
      </div>
    );
  }

  const uptimeH = Math.floor(status.uptime_s / 3600);
  const uptimeM = Math.floor((status.uptime_s % 3600) / 60);

  return (
    <div className="space-y-4 rounded-lg border p-4">
      {status.breach && (
        <div
          role="alert"
          className="rounded-lg bg-destructive px-3 py-2 text-center text-sm font-bold text-destructive-foreground"
        >
          SOVEREIGNTY BREACH: {status.breach}
        </div>
      )}

      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
          <svg className="h-5 w-5 text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold">Sovereignty Status</p>
          <p className="text-xs text-muted-foreground">
            {status.airgap_mode ? "Air-gapped" : "Network active"} · {status.blocked.toLocaleString()} blocked
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md bg-muted p-2">
          <span className="text-muted-foreground">Network</span>
          <p className="mt-0.5 font-mono font-medium">{status.network_mode}</p>
        </div>
        <div className="rounded-md bg-muted p-2">
          <span className="text-muted-foreground">DNS</span>
          <p className="mt-0.5 font-mono font-medium">{status.dns_resolvable ? "Resolvable" : "Blocked"}</p>
        </div>
        <div className="rounded-md bg-muted p-2">
          <span className="text-muted-foreground">Uptime</span>
          <p className="mt-0.5 font-mono font-medium">{uptimeH}h {uptimeM}m</p>
        </div>
        <div className="rounded-md bg-muted p-2">
          <span className="text-muted-foreground">Egressed</span>
          <p className="mt-0.5 font-mono font-medium">{status.bytes_egressed} B</p>
        </div>
      </div>

      {status.models.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-[10px] font-semibold uppercase text-muted-foreground">Local Models</span>
          {status.models.map((m) => (
            <div key={m.name} className="flex items-center gap-2 rounded-md bg-muted p-2 text-xs">
              <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-bold text-green-700 dark:bg-green-900 dark:text-green-300">
                LOCAL
              </span>
              <span className="font-medium">{m.role}</span>
              <span className="truncate font-mono text-muted-foreground">{m.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
