"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChatStore } from "@/store/chatStore";
import { useSessionStore } from "@/store/sessionStore";
import { useChatStream } from "@/hooks/useChatStream";
import { MessageList } from "@/components/chat/MessageList";
import { Composer } from "@/components/chat/Composer";
import { ApprovalCard } from "@/components/chat/ApprovalCard";
import { WorkbenchPanel } from "@/components/chat/WorkbenchPanel";
import { type SessionLayout } from "@/components/chat/LayoutPanel";
import { ScopePicker } from "@/components/chat/ScopePicker";
import { apiGet, apiPatch, apiPost } from "@/lib/api-client";
import type { ChatMessage } from "@/store/chatStore";

interface HistoryMessage {
  id: string;
  role: string;
  content: string;
  intent?: string | null;
  route_confidence?: number | null;
  grounded?: boolean | null;
  abstained?: boolean | null;
  citations: ChatMessage["citations"];
  reasoning: ChatMessage["reasoning"];
  sources: ChatMessage["sources"];
  files: ChatMessage["files"];
}

function toChatMessage(m: HistoryMessage): ChatMessage {
  const isAssistant = m.role === "assistant";
  return {
    id: m.id,
    role: isAssistant ? "assistant" : "user",
    content: m.content ?? "",
    intent: isAssistant && m.intent ? m.intent : undefined,
    grounded: m.grounded ?? undefined,
    abstained: m.abstained ?? undefined,
    citations: m.citations ?? [],
    sources: m.sources ?? [],
    reasoning: m.reasoning ?? [],
    files: m.files ?? [],
    route:
      isAssistant && m.intent
        ? { intent: m.intent, confidence: m.route_confidence ?? 0, rationale: "" }
        : undefined,
  };
}

interface DocMeta {
  id: string;
  filename: string;
  status: string;
}

export default function ChatPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id === "new" ? null : params.id;
  const sessionCreatedRef = useRef(false);
  const loadedForRef = useRef<string | null>(null);

  const [scopeDocIds, setScopeDocIds] = useState<string[]>([]);
  const [scopeTitles, setScopeTitles] = useState<Record<string, string>>({});
  const [availableDocs, setAvailableDocs] = useState<DocMeta[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [layoutOpen, setLayoutOpen] = useState(false);
  const [layoutData, setLayoutData] = useState<SessionLayout | null>(null);
  const [layoutLoading, setLayoutLoading] = useState(false);
  const [layoutError, setLayoutError] = useState<string | null>(null);

  const messages = useChatStore((s) => s.messages);
  const pendingApproval = useChatStore((s) => s.pendingApproval);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const clear = useChatStore((s) => s.clear);
  const setMessages = useChatStore((s) => s.setMessages);
  const user = useSessionStore((s) => s.user);
  const role = user?.role ?? "";
  const canScope = ["ENGINEER", "ANALYST", "ADMIN"].includes(role);

  useEffect(() => {
    if (useChatStore.getState().isStreaming) return; // don't yank the store mid-stream
    clear();
    setLayoutData(null);
    setLayoutError(null);
    sessionCreatedRef.current = false;
    loadedForRef.current = null;
  }, [sessionId, clear]);

  // Load the session's existing scope + history (persisted chat history).
  useEffect(() => {
    if (loadedForRef.current === (sessionId ?? "new")) return;
    loadedForRef.current = sessionId ?? "new";

    const titles: Record<string, string> = {};
    if (sessionId) {
      apiGet<{ document_ids?: string[]; document_id?: string | null }>(
        `/api/v1/chat/sessions/${sessionId}`
      )
        .then((meta) => {
          const ids = meta.document_ids && meta.document_ids.length
            ? meta.document_ids.filter(Boolean)
            : meta.document_id
              ? [meta.document_id]
              : [];
          setScopeDocIds(ids);
          return Promise.all(
            ids.map(async (id) => {
              try {
                const doc = await apiGet<{ id: string; filename: string }>(
                  `/api/v1/documents/${id}`
                );
                titles[doc.id] = doc.filename;
              } catch {
                titles[id] = id;
              }
            })
          );
        })
        .catch(() => {
          setScopeDocIds([]);
        })
        .finally(() => {
          setScopeTitles({ ...titles });
        });
    } else {
      setScopeDocIds([]);
      setScopeTitles({});
    }

    apiGet<{ items: DocMeta[] }>("/api/v1/documents?size=100&status=READY")
      .then((page) => setAvailableDocs((page.items ?? []).filter((d) => d.id && d.filename)))
      .catch(() => setAvailableDocs([]));

    apiGet<HistoryMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`)
      .then((history) => {
        if (useChatStore.getState().isStreaming) return; // stream will append live rows
        setMessages(history.map(toChatMessage));
      })
      .catch(() => {
        if (!useChatStore.getState().isStreaming) setMessages([]);
      });
  }, [sessionId, setMessages]);

  const applyScope = useCallback(
    async (ids: string[]) => {
      const next = [...new Set(ids)];
      setPickerOpen(false);
      setScopeDocIds(next);

      const buildTitles = () => {
        const t: Record<string, string> = {};
        for (const id of next) {
          const known = availableDocs.find((d) => d.id === id);
          t[id] = known?.filename ?? id;
        }
        return t;
      };

      const sid = useChatStore.getState().sessionId ?? sessionId;
      if (sid) {
        try {
          const meta = await apiPatch<{ document_ids: string[] }>(
            `/api/v1/chat/sessions/${sid}`,
            { document_ids: next }
          );
          const t = buildTitles();
          for (const id of meta.document_ids) if (!t[id]) t[id] = id;
          setScopeTitles(t);
        } catch (err) {
          console.error("scope update failed", err);
        }
      } else {
        setScopeTitles(buildTitles());
      }
    },
    [availableDocs, sessionId]
  );

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionId) return sessionId;
    if (sessionCreatedRef.current) return useChatStore.getState().sessionId;
    sessionCreatedRef.current = true;
    try {
      const res = await apiPost<{ id: string }>("/api/v1/chat/sessions", {
        title: "New Chat",
        document_ids: scopeDocIds.length ? scopeDocIds : undefined,
      });
      setSessionId(res.id);
      router.replace(`/chat/${res.id}`, { scroll: false });
      return res.id;
    } catch {
      sessionCreatedRef.current = false;
      return null;
    }
  }, [sessionId, scopeDocIds, setSessionId, router]);

  const activeSessionId = useChatStore((s) => s.sessionId);
  const { send, stop, isStreaming } = useChatStream({
    sessionId: activeSessionId || sessionId || "",
  });

  const fetchLayout = useCallback(async (sid: string) => {
    setLayoutLoading(true);
    setLayoutError(null);
    try {
      const data = await apiGet<SessionLayout>(`/api/v1/layouts/chat/sessions/${sid}`);
      setLayoutData(data);
    } catch (err) {
      setLayoutError((err as Error).message);
      setLayoutData(null);
    } finally {
      setLayoutLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!layoutOpen) return;
    const sid = activeSessionId || sessionId;
    if (sid) void fetchLayout(sid);
  }, [layoutOpen, activeSessionId, sessionId, scopeDocIds, fetchLayout]);

  async function handleSend(content: string, attachmentIds?: string[]) {
    const sid = await ensureSession();
    if (!sid) return;
    send(content, attachmentIds);
  }

  const toggleScope = (id: string) => {
    const next = scopeDocIds.includes(id)
      ? scopeDocIds.filter((d) => d !== id)
      : [...scopeDocIds, id];
    void applyScope(next);
  };

  const scopeNames = scopeDocIds.map((id) => scopeTitles[id] ?? id).filter(Boolean);
  const hasScope = scopeNames.length > 0;

  const suggestions = hasScope
    ? [
        "Summarise the scoped documents",
        "What are the key findings across these files?",
        "Are there any anomalies or issues?",
        "List the important recommendations in bullet points",
      ]
    : [
        "Summarise the CSB refinery incident report",
        "What does OSHA 3132 say about management of change?",
        "Which process safety clauses are relevant to PSM compliance?",
        "Explain the key findings in three bullet points",
      ];

  return (
    <div className="relative flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-white/10 bg-white/[0.03] px-4 py-1.5">
        <svg className="h-3.5 w-3.5 text-emerald-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-[11px] font-medium text-white/45">Chat scope</span>
        {hasScope ? (
          <div className="flex flex-wrap items-center gap-1">
            {scopeNames.map((name, i) => (
              <span key={scopeDocIds[i] ?? name} className="chat-pill px-2 py-0.5 text-[11px] text-foreground">
                {name}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-[11px] text-white/30">all documents</span>
        )}
        {canScope && (
          <button
            onClick={() => setPickerOpen((v) => !v)}
            className="ml-1 rounded-md border border-white/15 px-2 py-0.5 text-[11px] text-white/70 hover:bg-white/10 hover:text-white"
            title="Choose which files this chat uses"
          >
            {hasScope ? "change files" : "choose files"}
          </button>
        )}
        {!canScope && <span className="text-[11px] text-white/30">(your role cannot scope chats)</span>}
        <button
          onClick={() => setLayoutOpen((v) => !v)}
          className={`ml-auto flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] transition ${
            layoutOpen
              ? "border-emerald-400/40 bg-emerald-400/10 text-emerald-300"
              : "border-white/15 text-white/70 hover:bg-white/10 hover:text-white"
          }`}
          title="Open the workbench — page preview, DocLayout-YOLO regions, auto charts"
        >
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
          Workbench
        </button>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 flex-1 flex-col">
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            suggestions={messages.length === 0 ? suggestions : undefined}
            onSuggestion={(s) => handleSend(s)}
            onCitationClick={(n) => {
              const el = document.getElementById(`source-${n}`);
              el?.scrollIntoView({ behavior: "smooth", block: "center" });
            }}
          />
          <Composer onSend={handleSend} onStop={stop} isStreaming={isStreaming} />
        </div>
        {layoutOpen && (
          <WorkbenchPanel
            scopeDocIds={scopeDocIds}
            layoutData={layoutData}
            layoutLoading={layoutLoading}
            layoutError={layoutError}
            onClose={() => setLayoutOpen(false)}
            onRefreshLayout={() => {
              const sid = activeSessionId || sessionId;
              if (sid) void fetchLayout(sid);
            }}
          />
        )}
      </div>

      {pickerOpen && canScope && (
        <ScopePicker
          docs={availableDocs}
          selected={scopeDocIds}
          onToggle={toggleScope}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {pendingApproval && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40">
          <ApprovalCard
            tool={pendingApproval.tool}
            risk={pendingApproval.risk}
            arguments_={pendingApproval.arguments}
            rationale={pendingApproval.rationale}
            onApprove={async () => {
              const { setPendingApproval } = useChatStore.getState();
              const sid = activeSessionId || sessionId;
              if (sid) {
                try {
                  await apiPost(`/api/v1/chat/sessions/${sid}/approve`, {
                    approval_id: pendingApproval.approval_id,
                    decision: "APPROVED",
                  });
                } catch (err) {
                  console.error("approve failed", err);
                }
              }
              setPendingApproval(null);
            }}
            onDeny={async () => {
              const { setPendingApproval } = useChatStore.getState();
              const sid = activeSessionId || sessionId;
              if (sid) {
                try {
                  await apiPost(`/api/v1/chat/sessions/${sid}/approve`, {
                    approval_id: pendingApproval.approval_id,
                    decision: "DENIED",
                  });
                } catch (err) {
                  console.error("deny failed", err);
                }
              }
              setPendingApproval(null);
            }}
          />
        </div>
      )}
    </div>
  );
}