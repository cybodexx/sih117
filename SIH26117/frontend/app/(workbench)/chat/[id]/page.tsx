"use client";

import { useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChatStore } from "@/store/chatStore";
import { useChatStream } from "@/hooks/useChatStream";
import { MessageList } from "@/components/chat/MessageList";
import { Composer } from "@/components/chat/Composer";
import { ApprovalCard } from "@/components/chat/ApprovalCard";
import { apiPost } from "@/lib/api-client";

export default function ChatPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id === "new" ? null : params.id;
  const sessionCreatedRef = useRef(false);
  const messages = useChatStore((s) => s.messages);
  const pendingApproval = useChatStore((s) => s.pendingApproval);
  const setSessionId = useChatStore((s) => s.setSessionId);
  const clear = useChatStore((s) => s.clear);

  useEffect(() => {
    clear();
    sessionCreatedRef.current = false;
  }, [sessionId, clear]);

  const ensureSession = useCallback(async (): Promise<string | null> => {
    if (sessionId) return sessionId;
    if (sessionCreatedRef.current) return useChatStore.getState().sessionId;
    sessionCreatedRef.current = true;
    try {
      const res = await apiPost<{ id: string }>("/api/v1/chat/sessions", {
        title: "New Chat",
      });
      setSessionId(res.id);
      router.replace(`/chat/${res.id}`, { scroll: false });
      return res.id;
    } catch {
      sessionCreatedRef.current = false;
      return null;
    }
  }, [sessionId, setSessionId, router]);

  const activeSessionId = useChatStore((s) => s.sessionId);
  const { send, stop, isStreaming } = useChatStream({
    sessionId: activeSessionId || sessionId || "",
  });

  async function handleSend(content: string, attachmentIds?: string[]) {
    const sid = await ensureSession();
    if (!sid) return;
    send(content, attachmentIds);
  }

  const suggestions = [
    "Summarise the CSB refinery incident report",
    "What does OSHA 3132 say about management of change?",
    "Which process safety clauses are relevant to PSM compliance?",
    "Explain the key findings in three bullet points",
  ];

  return (
    <div className="relative flex h-full flex-col">
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
      {pendingApproval && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/40">
          <ApprovalCard
            tool={pendingApproval.tool}
            risk={pendingApproval.risk}
            arguments_={pendingApproval.arguments}
            rationale={pendingApproval.rationale}
            onApprove={() => {
              const { setPendingApproval } = useChatStore.getState();
              setPendingApproval(null);
            }}
            onDeny={() => {
              const { setPendingApproval } = useChatStore.getState();
              setPendingApproval(null);
            }}
          />
        </div>
      )}
    </div>
  );
}