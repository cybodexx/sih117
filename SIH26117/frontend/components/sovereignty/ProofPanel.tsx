"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api-client";
import { cn } from "@/lib/utils";

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
      <div className="rounded-2xl border border-border p-4 text-center text-sm text-destructive">
        Could not reach sovereignty endpoint.
      </div>
    );
  }

  if (!status) {
    return (
      <div className="animate-pulse space-y-4 rounded-2xl border border-border p-4">
        <div className="h-16 w-full rounded-xl bg-muted" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-20 rounded-xl bg-muted" />
          <div className="h-20 rounded-xl bg-muted" />
          <div className="h-20 rounded-xl bg-muted" />
          <div className="h-20 rounded-xl bg-muted" />
        </div>
      </div>
    );
  }

  const uptimeH = Math.floor(status.uptime_s / 3600);
  const uptimeM = Math.floor((status.uptime_s % 3600) / 60);
  const anyEgress = status.reached > 0 || status.bytes_egressed > 0;

  return (
    <div className="space-y-4">
      {status.breach && (
        <div
          role="alert"
          className="rounded-2xl bg-destructive px-3 py-2 text-center text-sm font-bold text-destructive-foreground"
        >
          SOVEREIGNTY BREACH: {status.breach}
        </div>
      )}

      <div className="flex items-center gap-4 rounded-2xl border border-border bg-card p-5">
        <div
          className={cn(
            "flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl",
            status.airgap_mode
              ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-300"
              : "bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-300",
          )}
        >
          <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold">Sovereignty Status</p>
          <p className="text-xs text-muted-foreground">
            {status.airgap_mode ? "Air-gapped — egress blocked" : "Network active"} ·{" "}
            {status.blocked.toLocaleString()} probes blocked
            {anyEgress && (
              <span className="ml-1 font-semibold text-destructive">
                · {" "}{status.reached} reached / {status.bytes_egressed} B egressed
              </span>
            )}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          label="Network"
          value={status.network_mode}
          icon={
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
          }
        />
        <StatCard
          label="DNS"
          value={status.dns_resolvable ? "Blocked" : "Isolated"}
          tone={status.dns_resolvable ? "danger" : "ok"}
          icon={
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064" />
          }
        />
        <StatCard
          label="Uptime"
          value={`${uptimeH}h ${uptimeM}m`}
          icon={
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          }
        />
        <StatCard
          label="Attempts"
          value={status.attempts.toLocaleString()}
          icon={
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
          }
        />
      </div>

      {status.models.length > 0 && (
        <div className="rounded-2xl border border-border bg-card p-4">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Local Models
          </span>
          <div className="mt-2 space-y-1.5">
            {status.models.map((m) => (
              <div
                key={m.name}
                className="flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2 text-xs"
              >
                <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-bold text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300">
                  LOCAL
                </span>
                <span className="font-medium">{m.role}</span>
                <span className="truncate font-mono text-muted-foreground">{m.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
  tone = "neutral",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  tone?: "neutral" | "ok" | "danger";
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-3.5">
      <div
        className={cn(
          "mb-2.5 flex h-8 w-8 items-center justify-center rounded-lg",
          tone === "neutral" && "bg-muted text-muted-foreground",
          tone === "ok" && "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/50 dark:text-emerald-300",
          tone === "danger" && "bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-300",
        )}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          {icon}
        </svg>
      </div>
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </span>
      <p className="mt-0.5 truncate font-mono text-sm font-medium">{value}</p>
    </div>
  );
}