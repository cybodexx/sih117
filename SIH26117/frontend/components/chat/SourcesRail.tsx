"use client";

interface SourceRef {
  n: number;
  document_title: string;
  page_start: number;
  score: number;
  snippet?: string;
}

interface SourcesRailProps {
  sources: SourceRef[];
}

export function SourcesRail({ sources }: SourcesRailProps) {
  if (sources.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground">
        Sources ({sources.length})
      </h4>
      <div className="space-y-1.5">
        {sources.map((s) => (
          <div
            key={s.n}
            id={`source-${s.n}`}
            className="rounded-lg border p-2.5 transition-colors hover:bg-accent"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded bg-primary/10 text-[10px] font-bold text-primary">
                    {s.n}
                  </span>
                  <span className="truncate text-xs font-medium">
                    {s.document_title}
                  </span>
                </div>
                <div className="mt-1 text-[10px] text-muted-foreground">
                  Page {s.page_start} · {(s.score * 100).toFixed(0)}% match
                </div>
              </div>
            </div>
            {s.snippet && (
              <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
                {s.snippet}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
