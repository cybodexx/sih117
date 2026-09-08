"use client";

import { useState } from "react";

interface DocMeta {
  id: string;
  filename: string;
  status: string;
}

export function ScopePicker({
  docs,
  selected,
  onToggle,
  onClose,
}: {
  docs: DocMeta[];
  selected: string[];
  onToggle: (id: string) => void;
  onClose: () => void;
}) {
  const [filter, setFilter] = useState("");

  const needle = filter.trim().toLowerCase();
  const visible = needle
    ? docs.filter((d) => d.filename.toLowerCase().includes(needle))
    : docs;

  return (
    <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="flex max-h-[80vh] w-full max-w-md flex-col overflow-hidden rounded-xl border border-white/15 bg-background-secondary shadow-2xl">
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-white/90">Chat files</h2>
            <p className="mt-0.5 text-[11px] text-white/45">
              Choose which documents this chat can read — answers will only use the
              files you select.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-white/50 hover:bg-white/10 hover:text-white"
            aria-label="Close"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="border-b border-white/10 px-4 py-2">
          <div className="flex gap-2">
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter by filename…"
              className="w-full rounded-md border border-white/15 bg-white/[0.04] px-2.5 py-1.5 text-xs text-white placeholder:text-white/30 focus:border-emerald-400/60 focus:outline-none"
            />
            <button
              onClick={() => selected.forEach(onToggle)}
              className="shrink-0 rounded-md border border-white/15 px-2.5 py-1.5 text-[11px] text-white/60 hover:bg-white/10 hover:text-white"
              title="Deselect all"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
          {visible.length === 0 && (
            <p className="px-2 py-4 text-center text-xs text-white/40">
              {filter ? "No files match the filter." : "No READY documents yet — upload files first."}
            </p>
          )}
          {visible.map((d) => {
            const active = selected.includes(d.id);
            return (
              <button
                key={d.id}
                onClick={() => onToggle(d.id)}
                className={`mb-1 flex w-full items-center gap-2.5 rounded-lg border px-3 py-2 text-left transition ${
                  active
                    ? "border-emerald-400/50 bg-emerald-400/10"
                    : "border-white/10 bg-white/[0.02] hover:bg-white/[0.06]"
                }`}
              >
                <span
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] font-bold transition ${
                    active
                      ? "border-emerald-400 bg-emerald-400 text-emerald-950"
                      : "border-white/30 text-transparent"
                  }`}
                >
                  ✓
                </span>
                <span className="truncate text-xs text-white/85">{d.filename}</span>
              </button>
            );
          })}
        </div>

        <div className="flex items-center justify-between border-t border-white/10 px-4 py-2.5">
          <span className="text-[11px] text-white/45">
            {selected.length} file{selected.length === 1 ? "" : "s"} selected
            {selected.length === 0 && " — chat falls back to all documents"}
          </span>
          <button
            onClick={onClose}
            className="rounded-md bg-emerald-400 px-3 py-1.5 text-xs font-semibold text-emerald-950 hover:bg-emerald-300"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}