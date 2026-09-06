"use client";

interface CitationChipProps {
  n: number;
  title?: string;
  onClick?: () => void;
}

export function CitationChip({ n, title, onClick }: CitationChipProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full border border-border bg-muted px-1.5 text-[10px] font-semibold text-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
      title={title ? `${title} — jump to source ${n}` : `Jump to source ${n}`}
    >
      {n}
    </button>
  );
}