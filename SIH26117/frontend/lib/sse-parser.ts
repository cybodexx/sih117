import { SSEFrame, RouteFrame, StepFrame, SourcesFrame, TokenFrame, ApprovalFrame, CitationsFrame, FileFrame, DoneFrame, ErrorFrame } from "./types";

interface ParseResult {
  frames: SSEFrame[];
  leftover: string;
}

export function parseSSE(raw: string): ParseResult {
  const frames: SSEFrame[] = [];
  let leftover = "";
  const chunks = raw.split("\n\n");

  for (let i = 0; i < chunks.length - 1; i++) {
    const chunk = chunks[i];
    if (!chunk.trim()) continue;

    let eventName = "message";
    let data = "";

    for (const line of chunk.split("\n")) {
      if (line.startsWith("event: ")) {
        eventName = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        data = line.slice(6);
      }
    }

    if (!data) continue;

    try {
      const parsed = JSON.parse(data);
      const frame = buildFrame(eventName, parsed);
      if (frame) frames.push(frame);
    } catch {
      // ignore malformed frames
    }
  }

  leftover = chunks[chunks.length - 1] || "";
  return { frames, leftover };
}

function buildFrame(event: string, data: unknown): SSEFrame | null {
  switch (event) {
    case "route":
      return { event: "route", data: data as RouteFrame };
    case "step":
      return { event: "step", data: data as StepFrame };
    case "sources":
      return { event: "sources", data: data as SourcesFrame };
    case "token":
      return { event: "token", data: data as TokenFrame };
    case "approval_required":
      return { event: "approval_required", data: data as ApprovalFrame };
    case "citations":
      return { event: "citations", data: data as CitationsFrame };
    case "file":
      return { event: "file", data: data as FileFrame };
    case "done":
      return { event: "done", data: data as DoneFrame };
    case "error":
      return { event: "error", data: data as ErrorFrame };
    default:
      return null;
  }
}

export function isTerminal(frame: SSEFrame): boolean {
  return frame.event === "done" || frame.event === "error";
}
