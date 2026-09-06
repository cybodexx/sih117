"use client";

import { useState, useRef, useCallback } from "react";
import { apiRequest } from "@/lib/api-client";

interface UploadState {
  progress: number;
  uploading: boolean;
  error: string | null;
}

interface UseUploadReturn extends UploadState {
  upload: (file: File) => Promise<string | null>;
  reset: () => void;
}

export function useUpload(): UseUploadReturn {
  const [state, setState] = useState<UploadState>({
    progress: 0,
    uploading: false,
    error: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const upload = useCallback(async (file: File): Promise<string | null> => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setState({ progress: 0, uploading: true, error: null });

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await apiRequest("/api/v1/documents", {
        method: "POST",
        body: formData,
        signal: abortRef.current.signal,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        setState({ progress: 0, uploading: false, error: err.detail });
        return null;
      }

      const data = await res.json();
      setState({ progress: 100, uploading: false, error: null });
      return data.document_id as string;
    } catch (err) {
      if ((err as Error).name === "AbortError") return null;
      setState({ progress: 0, uploading: false, error: "Upload failed" });
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ progress: 0, uploading: false, error: null });
  }, []);

  return { ...state, upload, reset };
}