"use client";

import { useRef, useCallback } from "react";
import { parseSSE, isTerminal } from "@/lib/sse-parser";
import type { SSEFrame } from "@/lib/types";
import { useChatStore } from "@/store/chatStore";
import { API_BASE } from "@/lib/api-base";

interface UseChatStreamOptions {
  sessionId: string;
  onComplete?: (frames: SSEFrame[]) => void;
}

export function useChatStream({ sessionId, onComplete }: UseChatStreamOptions) {
  const abortRef = useRef<AbortController | null>(null);
  const bufferRef = useRef("");
  const tokenBufferRef = useRef("");
  const rafRef = useRef<number | null>(null);
  const framesRef = useRef<SSEFrame[]>([]);

  const flushTokens = useCallback(() => {
    if (tokenBufferRef.current) {
      const msgs = useChatStore.getState().messages;
      const last = msgs.at(-1);
      if (last && last.role === "assistant") {
        useChatStore.getState().updateLastMessage({
          content: last.content + tokenBufferRef.current,
        });
      }
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

      const turnId = crypto.randomUUID();
      const msgId = crypto.randomUUID();
      const store = useChatStore.getState();

      store.addMessage({
        id: msgId,
        role: "user",
        content,
        citations: [],
        sources: [],
        reasoning: [],
      });
      store.addMessage({
        id: `assistant-${turnId}`,
        role: "assistant",
        content: "",
        citations: [],
        sources: [],
        reasoning: [],
      });
      store.setStreaming(true);

      try {
        const token = sessionStorage.getItem("access_token");
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const res = await fetch(
          `${API_BASE}/api/v1/chat/sessions/${sessionId}/messages`,
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

        const streamHeaders: Record<string, string> = {};
        if (token) streamHeaders["Authorization"] = `Bearer ${token}`;

        const params = new URLSearchParams({ turn_id: turnId });
        attachmentIds.forEach((id) => params.append("attachment_ids", id));

        const streamRes = await fetch(
          `${API_BASE}/api/v1/chat/sessions/${sessionId}/stream?${params.toString()}`,
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
              case "token":
                tokenBufferRef.current += frame.data.delta;
                if (!rafRef.current) {
                  rafRef.current = requestAnimationFrame(flushTokens);
                }
                break;
              case "step": {
                const lastMsg = useChatStore.getState().messages.at(-1);
                if (lastMsg) {
                  st.updateLastMessage({
                    reasoning: [
                      ...lastMsg.reasoning,
                      {
                        seq: frame.data.seq,
                        phase: frame.data.phase,
                        label: frame.data.label,
                        elapsed_ms: frame.data.elapsed_ms,
                      },
                    ],
                  });
                }
                break;
              }
              case "sources":
                st.updateLastMessage({ sources: frame.data.sources });
                break;
              case "citations":
                st.updateLastMessage({ citations: frame.data.citations });
                break;
              case "approval_required":
                st.setPendingApproval(frame.data);
                break;
              case "done":
                st.updateLastMessage({
                  grounded: frame.data.grounded,
                  abstained: frame.data.abstained,
                });
                break;
              case "error":
                st.updateLastMessage({ content: `Error: ${frame.data.message}` });
                break;
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
