"use client";

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
    <div className="w-full max-w-md rounded-xl border-2 border-amber-400 bg-card p-5 shadow-lg">
      <div className="mb-3 flex items-center gap-2">
        <svg className="h-5 w-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <h3 className="text-sm font-semibold">Approval Required</h3>
        <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-700 dark:bg-amber-900 dark:text-amber-300">
          {risk}
        </span>
      </div>
      <p className="mb-2 text-sm text-muted-foreground">{rationale}</p>
      <div className="mb-3 rounded-md bg-muted p-2">
        <span className="text-[10px] font-medium uppercase text-muted-foreground">Tool</span>
        <p className="font-mono text-sm">{tool}</p>
      </div>
      {Object.keys(arguments_).length > 0 && (
        <pre className="mb-3 max-h-32 overflow-auto rounded-md bg-muted p-2 font-mono text-xs scrollbar-thin">
          {JSON.stringify(arguments_, null, 2)}
        </pre>
      )}
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
        >
          Approve
        </button>
        <button
          onClick={onDeny}
          className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
        >
          Deny
        </button>
      </div>
    </div>
  );
}
