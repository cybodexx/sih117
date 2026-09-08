"use client";

import { useRef, useCallback } from "react";
import { parseSSE, isTerminal } from "@/lib/sse-parser";
import type { SSEFrame } from "@/lib/types";
import { useChatStore } from "@/store/chatStore";
import { API_BASE } from "@/lib/api-base";
import { getStoredToken } from "@/lib/api-client";

interface UseChatStreamOptions {
  sessionId: string;
  onComplete?: (frames: SSEFrame[]) => void;
}

function ensureAssistantLast(st: ReturnType<typeof useChatStore.getState>) {
  const msgs = st.messages;
  const last = msgs.at(-1);
  if (last && last.role === "assistant") return last;
  st.addMessage({
    id: `assistant-${crypto.randomUUID()}`,
    role: "assistant",
    content: "",
    citations: [],
    sources: [],
    reasoning: [],
    files: [],
  });
  const fresh = useChatStore.getState().messages;
  return fresh.at(-1)!;
}

export function useChatStream({ sessionId, onComplete }: UseChatStreamOptions) {
  const abortRef = useRef<AbortController | null>(null);
  const bufferRef = useRef("");
  const tokenBufferRef = useRef("");
  const rafRef = useRef<number | null>(null);
  const framesRef = useRef<SSEFrame[]>([]);

  const flushTokens = useCallback(() => {
    if (tokenBufferRef.current) {
      const st = useChatStore.getState();
      const last = ensureAssistantLast(st);
      st.updateLastMessage({
        content: last.content + tokenBufferRef.current,
      });
      tokenBufferRef.current = "";
    }
    rafRef.current = null;
  }, []);

  const send = useCallback(
    async (content: string, attachmentIds: string[] = []) => {
      abortRef.current?.abort();
      abortRef.current = new AbortController();
      framesRef.current = [];
      tokenBufferRef.current = "";
      bufferRef.current = "";

      // Resolve the session at call time: when a "New chat" is created, the
      // store is updated by ensureSession() *after* this hook was rendered, so
      // the prop closure may still hold "". Reading the store avoids POSTing to
      // /chat/sessions//messages.
      const effectiveSessionId = sessionId || useChatStore.getState().sessionId;
      if (!effectiveSessionId) {
        useChatStore.getState().updateLastMessage({
          content: "Error: no active session",
        });
        useChatStore.getState().setStreaming(false);
        return;
      }
      const msgId = crypto.randomUUID();
      const store = useChatStore.getState();

      store.addMessage({
        id: msgId,
        role: "user",
        content,
        citations: [],
        sources: [],
        reasoning: [],
        files: [],
      });
      store.addMessage({
        id: `assistant-${msgId}`,
        role: "assistant",
        content: "",
        citations: [],
        sources: [],
        reasoning: [],
        files: [],
      });
      store.setStreaming(true);

      try {
        const token = getStoredToken();
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(
          `${API_BASE}/api/v1/chat/sessions/${effectiveSessionId}/messages`,
          {
            method: "POST",
            headers,
            body: JSON.stringify({ content, attachment_ids: attachmentIds }),
            signal: abortRef.current.signal,
          }
        );

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: "Request failed" }));
          useChatStore.getState().updateLastMessage({ content: `Error: ${err.detail}` });
          useChatStore.getState().setStreaming(false);
          return;
        }

        const accepted = (await res.json()) as { turn_id: string };
        const turnId = accepted.turn_id;

        const streamHeaders: Record<string, string> = {};
        if (token) streamHeaders["Authorization"] = `Bearer ${token}`;

        const params = new URLSearchParams({ turn_id: turnId });
        attachmentIds.forEach((id) => params.append("attachment_ids", id));

        const streamRes = await fetch(
          `${API_BASE}/api/v1/chat/sessions/${effectiveSessionId}/stream?${params.toString()}`,
          {
            headers: streamHeaders,
            signal: abortRef.current.signal,
          }
        );

        const reader = streamRes.body?.getReader();
        if (!reader) {
          useChatStore.getState().setStreaming(false);
          return;
        }
        const decoder = new TextDecoder();

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          bufferRef.current += decoder.decode(value, { stream: true });
          const { frames, leftover } = parseSSE(bufferRef.current);
          bufferRef.current = leftover;

          for (const frame of frames) {
            framesRef.current.push(frame);
            const st = useChatStore.getState();
            switch (frame.event) {
              case "route": {
                const st = useChatStore.getState();
                ensureAssistantLast(st);
                st.updateLastMessage({
                  route: {
                    intent: frame.data.intent,
                    confidence: frame.data.confidence,
                    rationale: frame.data.rationale,
                    tier: frame.data.tier,
                    llm_used: frame.data.llm_used,
                  },
                });
                break;
              }
              case "token":
                tokenBufferRef.current += frame.data.delta;
                if (!rafRef.current) {
                  rafRef.current = requestAnimationFrame(flushTokens);
                }
                break;
              case "step": {
                const st = useChatStore.getState();
                const lastMsg = ensureAssistantLast(st);
                st.updateLastMessage({
                  reasoning: [
                    ...(lastMsg.reasoning ?? []),
                    {
                      seq: frame.data.seq,
                      phase: frame.data.phase,
                      label: frame.data.label,
                      elapsed_ms: frame.data.elapsed_ms,
                    },
                  ],
                });
                break;
              }
              case "sources": {
                const s2 = useChatStore.getState();
                ensureAssistantLast(s2);
                s2.updateLastMessage({ sources: frame.data.sources });
                break;
              }
              case "citations": {
                const s3 = useChatStore.getState();
                ensureAssistantLast(s3);
                s3.updateLastMessage({ citations: frame.data.citations });
                break;
              }
              case "file": {
                const st = useChatStore.getState();
                const last = ensureAssistantLast(st);
                const existing = last.files ?? [];
                if (
                  !existing.some(
                    (f) => f.deliverable_id === frame.data.deliverable_id
                  )
                ) {
                  st.updateLastMessage({
                    files: [
                      ...existing,
                      {
                        deliverable_id: frame.data.deliverable_id,
                        filename: frame.data.filename,
                        kind: frame.data.kind,
                        mime: frame.data.mime,
                        size_bytes: frame.data.size_bytes,
                      },
                    ],
                  });
                }
                break;
              }
              case "approval_required":
                st.setPendingApproval(frame.data);
                break;
              case "done": {
                const s4 = useChatStore.getState();
                ensureAssistantLast(s4);
                s4.updateLastMessage({
                  grounded: frame.data.grounded,
                  abstained: frame.data.abstained,
                });
                break;
              }
              case "error": {
                const s5 = useChatStore.getState();
                ensureAssistantLast(s5);
                s5.updateLastMessage({ content: `Error: ${frame.data.message}` });
                break;
              }
            }
          }

          if (frames.some(isTerminal)) break;
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          useChatStore.getState().updateLastMessage({ content: "Connection failed." });
        }
      } finally {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        flushTokens();
        useChatStore.getState().setStreaming(false);
        onComplete?.(framesRef.current);
        window.dispatchEvent(new CustomEvent("aegis:sessions-changed"));
      }
    },
    [sessionId, onComplete, flushTokens]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    useChatStore.getState().setStreaming(false);
  }, []);

  const isStreaming = useChatStore((s) => s.isStreaming);

  return { send, stop, isStreaming };
}
