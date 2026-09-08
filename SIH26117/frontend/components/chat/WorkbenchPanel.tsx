"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { apiGet } from "@/lib/api-client";
import { LayoutPanel, type SessionLayout } from "@/components/chat/LayoutPanel";

interface DocMeta {
  id: string;
  filename: string;
  mime: string;
  page_count: number;
  status: string;
}

interface LayoutBlock {
  class: string;
  confidence: number;
  bbox: number[];
}

interface LayoutPage {
  page: number;
  blocks: LayoutBlock[];
}

interface DocLayout {
  document_id: string;
  document_title: string;
  status: string;
  pages: LayoutPage[];
}

interface ChartDef {
  type: string;
  title: string;
  items?: { name: string; value: number }[];
  categories?: string[];
  x?: string[];
  series?: { name: string; data: (number | null)[] }[];
}

interface InsightsPayload {
  table: string;
  filename: string;
  rows: number;
  columns: { name: string; data_type: string; numeric: boolean }[];
  charts: ChartDef[];
  stats: { name: string; value: string; kind: string }[];
}

const CLASS_HEX: Record<string, string> = {
  title: "#34d399",
  "plain text": "#cbd5e1",
  text: "#cbd5e1",
  figure: "#a78bfa",
  table: "#38bdf8",
  "table caption": "#2dd4bf",
  "table footnote": "#2dd4bf",
  "isolate formula": "#fbbf24",
  formula: "#fbbf24",
  "formula caption": "#fb923c",
  caption: "#2dd4bf",
  header: "#9ca3af",
  footer: "#9ca3af",
  abandon: "#fb7185",
};

function classHex(k: string): string {
  const key = k.toLowerCase();
  if (CLASS_HEX[key]) return CLASS_HEX[key];
  for (const [prefix, color] of Object.entries(CLASS_HEX)) {
    if (key.includes(prefix)) return color;
  }
  return "#e2e8f0";
}

function PieChart({ chart }: { chart: ChartDef }) {
  const items = chart.items ?? [];
  const total = items.reduce((a, b) => a + b.value, 0) || 1;
  const palette = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#2dd4bf", "#fb923c", "#94a3b8"];
  const colors = items.map((_, i) => palette[i % palette.length]);
  let acc = 0;
  const stops = items
    .map((it, i) => {
      const from = (acc / total) * 360;
      acc += it.value;
      const to = (acc / total) * 360;
      return `${colors[i]} ${from}deg ${to}deg`;
    })
    .join(", ");
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
      <p className="mb-2 text-[11px] font-medium text-white/85">{chart.title}</p>
      <div className="flex items-center gap-3">
        <div
          className="h-20 w-20 shrink-0 rounded-full"
          style={{ background: `conic-gradient(${stops})` }}
          title={`total ${total}`}
        />
        <div className="min-w-0 flex-1 space-y-1">
          {items.map((it, i) => (
            <div key={it.name} className="flex items-center gap-2 text-[10px]">
              <span className="h-2 w-2 rounded-full" style={{ background: colors[i] }} />
              <span className="truncate text-white/70">{it.name}</span>
              <span className="ml-auto font-mono text-white/50">{it.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function BarChart({ chart }: { chart: ChartDef }) {
  const cats = chart.categories ?? [];
  const values = (chart.series?.[0]?.data ?? []).map((v) => v ?? 0);
  const max = Math.max(...values, 1);
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
      <p className="mb-2 text-[11px] font-medium text-white/85">{chart.title}</p>
      <div className="flex h-32 items-end gap-1.5">
        {values.map((v, i) => (
          <div key={`${cats[i]}-${i}`} className="group relative flex min-w-0 flex-1 flex-col items-center">
            <div
              className="w-full rounded-t bg-sky-400/80"
              style={{ height: `${Math.max(4, (v / max) * 100)}%` }}
              title={`${cats[i]}: ${v}`}
            />
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-1.5">
        {cats.map((c, i) => (
          <span key={i} className="min-w-0 flex-1 truncate text-center text-[9px] text-white/40" title={c}>
            {c.length > 10 ? `${c.slice(0, 10)}…` : c}
          </span>
        ))}
      </div>
    </div>
  );
}

function LineChart({ chart }: { chart: ChartDef }) {
  const x = chart.x ?? [];
  const series = chart.series ?? [];
  const W = 260;
  const H = 110;
  const PAD = 6;
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
      <p className="mb-2 text-[11px] font-medium text-white/85">{chart.title}</p>
      {series.map((s) => {
        const vals = s.data ?? [];
        const clean = vals.filter((v): v is number => v !== null && v !== undefined);
        if (!clean.length) return null;
        const min = Math.min(...clean);
        const max = Math.max(...clean);
        const span = max - min || 1;
        const pts = vals
          .map((v, i) => {
            if (v === null || v === undefined) return null;
            const px = PAD + (i / Math.max(vals.length - 1, 1)) * (W - PAD * 2);
            const py = PAD + (1 - (v - min) / span) * (H - PAD * 2);
            return `${px},${py}`;
          })
          .filter(Boolean)
          .join(" ");
        const last = vals.length - 1;
        return (
          <svg key={s.name} viewBox={`0 0 ${W} ${H}`} className="h-28 w-full">
            <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
            <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
            <polyline
              points={pts}
              fill="none"
              stroke="#34d399"
              strokeWidth={1.5}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            <circle
              cx={PAD + (last / Math.max(vals.length - 1, 1)) * (W - PAD * 2)}
              cy={PAD + (1 - ((vals[last] ?? 0) - min) / span) * (H - PAD * 2)}
              r={2.5}
              fill="#34d399"
            />
          </svg>
        );
      })}
      <div className="mt-1 flex justify-between text-[9px] text-white/35">
        <span>{x[0] ?? ""}</span>
        <span>{x[x.length - 1] ?? ""}</span>
      </div>
    </div>
  );
}

function ChartCard({ chart }: { chart: ChartDef }) {
  if (chart.type === "pie") return <PieChart chart={chart} />;
  if (chart.type === "line") return <LineChart chart={chart} />;
  return <BarChart chart={chart} />;
}

function PreviewPane({
  doc,
  page,
  setPage,
  layout,
  showBoxes,
  setShowBoxes,
}: {
  doc: DocMeta;
  page: number;
  setPage: (p: number) => void;
  layout: DocLayout | null;
  showBoxes: boolean;
  setShowBoxes: (v: boolean) => void;
}) {
  const [imgError, setImgError] = useState(false);
  const isImage = doc.mime.startsWith("image/");
  const url = `/api/v1/documents/${doc.id}/preview${isImage ? "" : `?page=${page}`}`;
  const blocks = useMemo(() => {
    if (!showBoxes || !layout) return [];
    return (layout.pages.find((p) => p.page === page)?.blocks ?? []).filter(
      (b) => b.class !== "abandon"
    );
  }, [showBoxes, layout, page]);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {!isImage && doc.page_count > 1 && (
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="rounded-md border border-white/15 px-2 py-0.5 text-[11px] text-white/70 hover:bg-white/10 disabled:opacity-30"
            >
              ‹
            </button>
            <span className="font-mono text-[10px] text-white/50">
              page {page}/{doc.page_count}
            </span>
            <button
              onClick={() => setPage(Math.min(doc.page_count, page + 1))}
              disabled={page >= doc.page_count}
              className="rounded-md border border-white/15 px-2 py-0.5 text-[11px] text-white/70 hover:bg-white/10 disabled:opacity-30"
            >
              ›
            </button>
          </div>
        )}
        <label className="ml-auto flex cursor-pointer items-center gap-1.5 text-[10px] text-white/55">
          <input
            type="checkbox"
            checked={showBoxes}
            onChange={(e) => setShowBoxes(e.target.checked)}
            className="accent-emerald-400"
          />
          overlay layout regions
        </label>
      </div>

      <div className="relative overflow-hidden rounded-lg border border-white/10 bg-black/40">
        {imgError ? (
          <p className="px-3 py-6 text-center text-[11px] text-white/40">
            Preview unavailable for this file type.
          </p>
        ) : (
          <img
            key={url}
            src={url}
            alt={doc.filename}
            className="block h-auto w-full"
            onError={() => setImgError(true)}
            onLoad={() => setImgError(false)}
          />
        )}
        {!imgError &&
          blocks.map((b, i) => (
            <div
              key={`${b.class}-${i}`}
              className="pointer-events-none absolute rounded-sm border"
              style={{
                left: `${b.bbox[0] * 100}%`,
                top: `${b.bbox[1] * 100}%`,
                width: `${(b.bbox[2] - b.bbox[0]) * 100}%`,
                height: `${(b.bbox[3] - b.bbox[1]) * 100}%`,
                borderColor: classHex(b.class),
                background: `${classHex(b.class)}1f`,
              }}
              title={`${b.class} · ${(b.confidence * 100).toFixed(0)}%`}
            >
              <span
                className="absolute -top-4 left-0 whitespace-nowrap rounded px-1 py-px font-mono text-[8px] font-semibold"
                style={{ background: classHex(b.class), color: "#0b0b0d" }}
              >
                {b.class} {(b.confidence * 100).toFixed(0)}%
              </span>
            </div>
          ))}
      </div>

      {layout && layout.status !== "NOT_ANALYSED" && (
        <div className="flex flex-wrap gap-1">
          {[...new Set(layout.pages.flatMap((p) => p.blocks.map((b) => b.class)))].map((k) => (
            <span
              key={k}
              className="rounded px-1.5 py-0.5 font-mono text-[9px] font-medium"
              style={{ background: `${classHex(k)}26`, color: classHex(k), border: `1px solid ${classHex(k)}66` }}
            >
              {k}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function InsightsPane({ doc }: { doc: DocMeta }) {
  const [data, setData] = useState<InsightsPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loadedFor = useRef<string | null>(null);

  useEffect(() => {
    if (loadedFor.current === doc.id) return;
    loadedFor.current = doc.id;
    setLoading(true);
    setError(null);
    setData(null);
    apiGet<InsightsPayload>(`/api/v1/insights/documents/${doc.id}`)
      .then((p) => setData(p))
      .catch((err) => {
        const m = (err as Error).message || "";
        setError(m.includes("tabular") ? "no-charts" : m);
      })
      .finally(() => setLoading(false));
  }, [doc.id]);

  if (loading) {
    return (
      <div className="space-y-2">
        <div className="h-3 w-2/3 animate-pulse rounded bg-white/10" />
        <div className="h-28 animate-pulse rounded-lg bg-white/[0.05]" />
      </div>
    );
  }
  if (error === "no-charts") {
    return (
      <p className="rounded-md border border-white/10 bg-white/[0.02] px-3 py-2 text-[11px] text-white/50">
        No charts available — this file has no tabular data to aggregate.
      </p>
    );
  }
  if (error) {
    return (
      <p className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
        {error}
      </p>
    );
  }
  if (!data) return null;

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-white/40">
        {data.rows.toLocaleString()} rows from <span className="font-mono text-white/60">{data.table}</span> · computed
        directly from the data — no AI guesses.
      </p>
      {data.charts.map((c, i) => (
        <ChartCard key={`${c.title}-${i}`} chart={c} />
      ))}
      {data.stats.length > 0 && (
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <p className="mb-2 text-[11px] font-medium text-white/85">Column stats</p>
          <div className="space-y-1">
            {data.stats.map((s) => (
              <div key={s.name} className="flex items-baseline gap-2 text-[10px]">
                <span className="shrink-0 font-mono text-white/55">{s.name}</span>
                <span className="truncate text-white/40">{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const PanelTab = ({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) => (
  <button
    onClick={onClick}
    className={`rounded-md px-2.5 py-1 text-[11px] transition ${
      active
        ? "bg-emerald-400/15 text-emerald-300"
        : "text-white/55 hover:bg-white/5 hover:text-white/80"
    }`}
  >
    {children}
  </button>
);

export function WorkbenchPanel({
  scopeDocIds,
  layoutData,
  layoutLoading,
  layoutError,
  onClose,
  onRefreshLayout,
}: {
  scopeDocIds: string[];
  layoutData: SessionLayout | null;
  layoutLoading: boolean;
  layoutError: string | null;
  onClose: () => void;
  onRefreshLayout: () => void;
}) {
  const [tab, setTab] = useState<"preview" | "layout" | "insights">("preview");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [docInfo, setDocInfo] = useState<Record<string, DocMeta>>({});
  const [page, setPage] = useState(1);
  const [showBoxes, setShowBoxes] = useState(true);
  const [docLayout, setDocLayout] = useState<DocLayout | null>(null);
  const [layoutFetching, setLayoutFetching] = useState(false);
  const [layoutErr, setLayoutErr] = useState<string | null>(null);
  const autoTabSet = useRef(false);

  const docs = useMemo(() => {
    const list = scopeDocIds.map((id) => docInfo[id]).filter(Boolean) as DocMeta[];
    return list;
  }, [scopeDocIds, docInfo]);

  const currentId = selectedId ?? scopeDocIds[0] ?? null;
  const currentDoc = currentId ? docInfo[currentId] ?? null : null;

  useEffect(() => {
    if (scopeDocIds.length === 0) {
      setSelectedId(null);
      setPage(1);
      return;
    }
    setSelectedId((s) => (s && scopeDocIds.includes(s) ? s : scopeDocIds[0]));
  }, [scopeDocIds]);

  // Fetch meta for each scoped doc.
  useEffect(() => {
    for (const id of scopeDocIds) {
      if (docInfo[id]) continue;
      apiGet<DocMeta>(`/api/v1/documents/${id}`)
        .then((d) => setDocInfo((prev) => ({ ...prev, [id]: d })))
        .catch(() => {});
    }
  }, [scopeDocIds, docInfo]);

  // For spreadsheets, jump straight to the charts so the AI shows graphs by default.
  useEffect(() => {
    if (!currentDoc || autoTabSet.current) return;
    const m = (currentDoc.mime ?? "").toLowerCase();
    if (m.includes("csv") || m.includes("excel") || m.includes("spreadsheet")) {
      autoTabSet.current = true;
      setTab("insights");
    }
  }, [currentDoc]);

  // Reset page / fetch layout when doc selection changes.
  useEffect(() => {
    setPage(1);
    if (!currentId) {
      setDocLayout(null);
      return;
    }
    setLayoutFetching(true);
    setLayoutErr(null);
    apiGet<DocLayout>(`/api/v1/layouts/documents/${currentId}`)
      .then((l) => setDocLayout(l))
      .catch((err) => setLayoutErr((err as Error).message))
      .finally(() => setLayoutFetching(false));
  }, [currentId]);

  return (
    <aside className="flex h-full w-[360px] shrink-0 flex-col border-l border-white/10 bg-background-secondary">
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-xs font-semibold text-white/90">Workbench</h2>
          <p className="mt-0.5 truncate text-[10px] text-white/40">
            {currentDoc ? currentDoc.filename : scopeDocIds.length ? "loading…" : "no documents scoped"}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {docs.length > 1 && (
            <select
              value={currentId ?? ""}
              onChange={(e) => {
                setSelectedId(e.target.value || null);
                setPage(1);
              }}
              className="max-w-[130px] rounded-md border border-white/15 bg-background px-1.5 py-1 text-[10px] text-white/75"
              title="Choose which scoped file to inspect"
            >
              {docs.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename.length > 22 ? `${d.filename.slice(0, 22)}…` : d.filename}
                </option>
              ))}
            </select>
          )}
          <button
            onClick={onClose}
            className="rounded-md p-1 text-white/50 hover:bg-white/10 hover:text-white"
            title="Close workbench panel"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex items-center gap-1 border-b border-white/10 px-3 py-2">
        <PanelTab active={tab === "preview"} onClick={() => setTab("preview")}>
          Preview
        </PanelTab>
        <PanelTab active={tab === "layout"} onClick={() => setTab("layout")}>
          Layout
        </PanelTab>
        <PanelTab active={tab === "insights"} onClick={() => setTab("insights")}>
          Insights
        </PanelTab>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">
        {!currentId && (
          <p className="text-[11px] text-white/35">
            No documents are scoped to this chat. Use “change files” above to pin files to the workbench.
          </p>
        )}

        {currentId && tab === "preview" && currentDoc && (
          <PreviewPane
            doc={currentDoc}
            page={page}
            setPage={setPage}
            layout={docLayout}
            showBoxes={showBoxes}
            setShowBoxes={setShowBoxes}
          />
        )}

        {currentId && tab === "layout" && (
          <div className="space-y-2">
            {layoutFetching && (
              <div className="space-y-2">
                <div className="h-3 w-2/3 animate-pulse rounded bg-white/10" />
                <div className="h-24 animate-pulse rounded-lg bg-white/[0.05]" />
              </div>
            )}
            {layoutErr && (
              <p className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
                {layoutErr}
              </p>
            )}
            {!layoutFetching && !layoutErr && layoutData && (
              <LayoutPanel
                data={layoutData}
                loading={layoutLoading}
                error={layoutError}
                onClose={() => {}}
                onRefresh={onRefreshLayout}
              />
            )}
          </div>
        )}

        {currentId && tab === "insights" && currentDoc && <InsightsPane doc={currentDoc} />}
      </div>
    </aside>
  );
}