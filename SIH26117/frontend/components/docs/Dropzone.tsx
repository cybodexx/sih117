"use client";

import { useState, useRef, useCallback, type DragEvent } from "react";
import { cn } from "@/lib/utils";

interface DropzoneProps {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
}

export function Dropzone({
  onFiles,
  accept = ".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.txt,.md,.log,.csv,.json,.docx,.pptx,.xlsx,.xls",
  multiple = true,
}: DropzoneProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCountRef = useRef(0);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      onFiles(Array.from(fileList));
    },
    [onFiles]
  );

  function handleDragEnter(e: DragEvent) {
    e.preventDefault();
    dragCountRef.current++;
    setDragging(true);
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault();
    dragCountRef.current--;
    if (dragCountRef.current === 0) setDragging(false);
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragCountRef.current = 0;
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 transition-colors",
        dragging
          ? "border-white/60 bg-white/5"
          : "border-white/15 hover:border-white/40 hover:bg-white/[0.04]"
      )}
    >
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-white text-black shadow-[0_0_24px_rgba(255,255,255,0.25),inset_0_1px_0_rgba(255,255,255,0.9)]">
        <svg
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 16V4m0 0L8 8m4-4l4 4M4 14v4a2 2 0 002 2h12a2 2 0 002-2v-4"
          />
        </svg>
      </div>
      <p className="text-sm font-medium">
        {dragging ? "Drop files here" : "Click or drag files to upload"}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        PDF, images, text, CSV, Excel, Word, PPT — air-gapped
      </p>
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(e) => handleFiles(e.target.files)}
        className="hidden"
      />
    </div>
  );
}
