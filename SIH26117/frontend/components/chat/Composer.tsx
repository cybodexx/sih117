"use client";

import { useState, useRef, useEffect, useCallback, type DragEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { API_BASE } from "@/lib/api-base";
import { getStoredToken } from "@/lib/api-client";

interface ComposerProps {
  onSend: (content: string, attachmentIds?: string[]) => void;
  onStop?: () => void;
  isStreaming?: boolean;
}

interface AttachmentChip {
  id: string;
  name: string;
  status: "uploading" | "ready" | "error";
  error?: string;
}

async function uploadFile(file: File): Promise<{ attachment_id: string }> {
  const token = getStoredToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/attachments`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

export function Composer({ onSend, onStop, isStreaming }: ComposerProps) {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<AttachmentChip[]>([]);
  const [dragging, setDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const addFiles = useCallback((files: File[]) => {
    const images = files.filter((f) => f.type.startsWith("image/"));
    for (const file of images.slice(0, 3 - attachments.length)) {
      let id = "";
      setAttachments((prev) => {
        if (prev.length >= 3) return prev;
        id = crypto.randomUUID();
        return [...prev, { id, name: file.name, status: "uploading" }];
      });
      if (!id) continue;
      uploadFile(file)
        .then((res) =>
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id
                ? { ...a, id: res.attachment_id, status: "ready" }
                : a
            )
          )
        )
        .catch((err: Error) =>
          setAttachments((prev) =>
            prev.map((a) =>
              a.id === id ? { ...a, status: "error", error: err.message } : a
            )
          )
        );
    }
  }, [attachments.length]);

  const readyIds = attachments
    .filter((a) => a.status === "ready")
    .map((a) => a.id);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if ((!trimmed && readyIds.length === 0) || attachments.some((a) => a.status === "uploading"))
      return;
    onSend(trimmed, readyIds);
    setValue("");
    setAttachments([]);
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  }, [value, readyIds, attachments, onSend]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (isStreaming) return;
      handleSubmit();
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    const items = Array.from(e.clipboardData.items);
    const imageItem = items.find((i) => i.type.startsWith("image/"));
    if (imageItem) {
      e.preventDefault();
      const file = imageItem.getAsFile();
      if (file) addFiles([file]);
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      addFiles([file]);
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    setDragging(true);
  }

  function handleDragLeave() {
    setDragging(false);
  }

  const canSend =
    (value.trim().length > 0 || readyIds.length > 0) &&
    !isStreaming &&
    !attachments.some((a) => a.status === "uploading");

  return (
    <div
      className={`flex-shrink-0 border-t border-white/10 bg-black px-4 pb-3 pt-3 transition-colors ${
        dragging ? "bg-white/5" : ""
      }`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <div className="mx-auto max-w-3xl">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files?.length) addFiles(Array.from(e.target.files));
            e.target.value = "";
          }}
        />
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {attachments.map((a, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs ${
                  a.status === "error"
                    ? "border-destructive/40 bg-destructive/10 text-destructive"
                    : "border-border bg-muted/60 text-muted-foreground"
                }`}
                title={a.error}
              >
                {a.status === "uploading" ? (
                  <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                ) : a.status === "ready" ? (
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                )}
                <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {a.name}
                <button
                  onClick={() => setAttachments((p) => p.filter((_, j) => j !== i))}
                  className="text-foreground hover:text-destructive"
                  aria-label="Remove attachment"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="chat-input-shadow flex items-end gap-1 rounded-[28px] border border-white/15 bg-white/[0.05] p-2 pl-4 backdrop-blur-md transition-colors focus-within:border-white/35">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="mb-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground"
            aria-label="Attach a photo"
            title="Attach a photo of the equipment"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <path d="M21 15l-5-5L5 21" />
            </svg>
          </button>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={isStreaming ? "Generating…" : "Ask AEGIS-WB anything about your documents"}
            rows={1}
            className="max-h-[200px] min-h-[26px] flex-1 resize-none bg-transparent py-1.5 text-[15px] focus:outline-none placeholder:text-muted-foreground/70"
          />
          <AnimatePresence mode="wait" initial={false}>
            {isStreaming ? (
              <motion.button
                key="stop"
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.6, opacity: 0 }}
                whileTap={{ scale: 0.88 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                onClick={onStop}
                className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-white transition-colors hover:border-red-400/40 hover:bg-red-500/15 hover:text-red-200"
                aria-label="Stop generating"
              >
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="7" y="7" width="10" height="10" rx="2" />
                </svg>
              </motion.button>
            ) : (
              <motion.button
                key="send"
                initial={{ scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.6, opacity: 0 }}
                whileTap={{ scale: 0.88 }}
                transition={{ type: "spring", stiffness: 300, damping: 20 }}
                onClick={handleSubmit}
                disabled={!canSend}
                className="liquid-btn-solid flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full disabled:opacity-25"
                aria-label="Send message"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        <p className="mt-2.5 flex items-center justify-center gap-1.5 text-center text-[11px] leading-relaxed text-muted-foreground">
          <svg className="h-3.5 w-3.5 text-emerald-500/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          AEGIS-WB can make mistakes. Check important information. Air-gapped —
          documents and queries never leave this machine.
        </p>
      </div>
    </div>
  );
}