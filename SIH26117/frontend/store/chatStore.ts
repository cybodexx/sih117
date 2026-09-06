"use client";

import { create } from "zustand";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  intent?: string;
  grounded?: boolean;
  abstained?: boolean;
  citations: Array<{
    n: number;
    document_id: string;
    document_title: string;
    page: number;
    bbox?: number[];
    snippet: string;
  }>;
  sources: Array<{
    n: number;
    document_title: string;
    page_start: number;
    score: number;
  }>;
  reasoning: Array<{
    seq: number;
    phase: string;
    label?: string;
    elapsed_ms?: number;
  }>;
}

export interface ApprovalRequest {
  approval_id?: string;
  tool: string;
  risk: string;
  arguments: Record<string, unknown>;
  rationale: string;
  expires_at?: string;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  sessionId: string | null;
  pendingApproval: ApprovalRequest | null;

  addMessage: (msg: ChatMessage) => void;
  updateLastMessage: (update: Partial<ChatMessage>) => void;
  setStreaming: (v: boolean) => void;
  setSessionId: (id: string) => void;
  setPendingApproval: (v: ApprovalRequest | null) => void;
  clear: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  sessionId: null,
  pendingApproval: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  updateLastMessage: (update) =>
    set((s) => ({
      messages: s.messages.map((m, i) =>
        i === s.messages.length - 1 ? { ...m, ...update } : m
      ),
    })),
  setStreaming: (v) => set({ isStreaming: v }),
  setSessionId: (id) => set({ sessionId: id }),
  setPendingApproval: (v) => set({ pendingApproval: v }),
  clear: () => set({ messages: [], sessionId: null }),
}));
