"use client";

import { create } from "zustand";

interface FlagsState {
  airgapMode: boolean;
  rerankerEnabled: boolean;
  ocrEnabled: boolean;
  visionEnabled: boolean;
  setFlag: (key: keyof FlagsState, value: boolean) => void;
}

export const useFlagsStore = create<FlagsState>((set) => ({
  airgapMode: false,
  rerankerEnabled: true,
  ocrEnabled: true,
  visionEnabled: true,
  setFlag: (key, value) => set({ [key]: value }),
}));
