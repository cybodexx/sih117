"use client";

import { useState } from "react";
import { cn, formatTime } from "@/lib/utils";

interface ReasoningStep {
  seq: number;
  phase: string;
  label?: string;
  tool?: string;
  tool_args?: Record<string, unknown>;
  detail?: string;
  elapsed_ms?: number;
}

interface ReasoningTraceProps {
  steps: ReasoningStep[];
  isStreaming?: boolean;
}

const PHASE_COLOR: Record<string, string> = {
  plan: "bg-blue-500",
  reason: "bg-purple-500",
  act: "bg-orange-500",
  observe: "bg-cyan-500",
  reflect: "bg-yellow-500",
  synthesize: "bg-green-500",
};

export function ReasoningTrace({ steps, isStreaming }: ReasoningTraceProps) {
  const [expanded, setExpanded] = useState(false);

  if (steps.length === 0) return null;

  const totalTime = steps.reduce((sum, s) => sum + (s.elapsed_ms || 0), 0);

  return (
    <div className="rounded-lg border bg-background/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-xs"
        aria-expanded={expanded}
      >
        <span className="text-muted-foreground">
          {isStreaming ? "Reasoning..." : `${steps.length} steps`}
          {!isStreaming && ` · ${formatTime(totalTime)}`}
        </span>
        <svg
          className={cn(
            "h-3 w-3 text-muted-foreground transition-transform",
            expanded && "rotate-180"
          )}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && (
        <ol className="border-t">
          {steps.map((step) => (
            <li
              key={step.seq}
              className="flex items-start gap-2 px-3 py-1.5 text-xs"
            >
              <span
                className={cn(
                  "mt-1 h-2 w-2 flex-shrink-0 rounded-full",
                  PHASE_COLOR[step.phase] || "bg-gray-400"
                )}
              />
              <div className="flex-1 min-w-0">
                <span className="font-medium">{step.phase}</span>
                {step.label && (
                  <span className="ml-1.5 text-muted-foreground">
                    {step.label}
                  </span>
                )}
                {step.tool && (
                  <span className="ml-1.5 rounded bg-muted px-1 py-0.5 font-mono text-[10px]">
                    {step.tool}
                  </span>
                )}
              </div>
              {step.elapsed_ms != null && (
                <span className="text-muted-foreground whitespace-nowrap">
                  {formatTime(step.elapsed_ms)}
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
