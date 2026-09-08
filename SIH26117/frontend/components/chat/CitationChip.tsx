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
      className="inline-flex h-5 min-w-[20px] cursor-pointer items-center justify-center rounded-full border border-white/15 bg-white/[0.06] px-1.5 text-[10px] font-semibold text-white/80 transition-colors hover:border-white/50 hover:bg-white/10 hover:text-white"
      title={title ? `${title} — jump to source ${n}` : `Jump to source ${n}`}
    >
      {n}
    </button>
  );
}