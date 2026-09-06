export type SSEFrame =
  | { event: "route"; data: RouteFrame }
  | { event: "step"; data: StepFrame }
  | { event: "sources"; data: SourcesFrame }
  | { event: "token"; data: TokenFrame }
  | { event: "approval_required"; data: ApprovalFrame }
  | { event: "citations"; data: CitationsFrame }
  | { event: "done"; data: DoneFrame }
  | { event: "error"; data: ErrorFrame };

export interface RouteFrame {
  intent: string;
  confidence: number;
  rationale: string;
  sub_queries?: string[];
}

export interface StepFrame {
  seq: number;
  phase: "plan" | "reason" | "act" | "observe" | "reflect" | "synthesize";
  label?: string;
  tool?: string;
  tool_args?: Record<string, unknown>;
  detail?: string;
  elapsed_ms?: number;
}

export interface SourcesFrame {
  sources: Array<{
    n: number;
    chunk_id: string;
    document_id: string;
    document_title: string;
    page_start: number;
    page_end: number;
    score: number;
    chunk_type: string;
    suspected_injection: boolean;
    snippet: string;
  }>;
}

export interface TokenFrame {
  delta: string;
}

export interface ApprovalFrame {
  approval_id: string;
  tool: string;
  risk: string;
  arguments: Record<string, unknown>;
  rationale: string;
  expires_at: string;
}

export interface CitationsFrame {
  citations: Array<{
    n: number;
    document_id: string;
    document_title: string;
    page: number;
    bbox?: number[];
    snippet: string;
  }>;
}

export interface DoneFrame {
  message_id: string;
  turn_id: string;
  grounded: boolean;
  abstained: boolean;
  citation_coverage: number;
  tokens_in: number;
  tokens_out: number;
  latency_ms: number;
  tool_calls: number;
}

export interface ErrorFrame {
  code: string;
  message: string;
  retryable: boolean;
  correlation_id?: string;
}
