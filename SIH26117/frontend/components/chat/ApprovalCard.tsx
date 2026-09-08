"use client";

import { motion } from "framer-motion";

interface ApprovalCardProps {
  tool: string;
  risk: string;
  arguments_: Record<string, unknown>;
  rationale: string;
  onApprove: () => void;
  onDeny: () => void;
}

export function ApprovalCard({
  tool,
  risk,
  arguments_,
  rationale,
  onApprove,
  onDeny,
}: ApprovalCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 24 }}
      className="w-full max-w-md rounded-2xl border border-amber-400/60 bg-card p-5 shadow-2xl shadow-black/40 backdrop-blur"
      role="alertdialog"
      aria-label="Tool approval required"
    >
      <div className="mb-3 flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </span>
        <h3 className="text-sm font-semibold">Approval Required</h3>
        <span className="ml-auto rounded bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700 dark:bg-amber-900 dark:text-amber-300">
          {risk}
        </span>
      </div>
      <p className="mb-2 text-sm text-muted-foreground">{rationale}</p>
      <div className="mb-3 rounded-lg bg-muted p-2.5">
        <span className="text-[10px] font-medium uppercase text-muted-foreground">Tool</span>
        <p className="mt-0.5 font-mono text-sm">{tool}</p>
      </div>
      {Object.keys(arguments_).length > 0 && (
        <pre className="mb-3 max-h-36 overflow-auto rounded-lg bg-muted p-2.5 font-mono text-xs scrollbar-thin">
          {JSON.stringify(arguments_, null, 2)}
        </pre>
      )}
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className="flex-1 cursor-pointer rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
        >
          Approve
        </button>
        <button
          onClick={onDeny}
          className="flex-1 cursor-pointer rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
        >
          Deny
        </button>
      </div>
    </motion.div>
  );
}