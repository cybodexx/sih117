"use client";

import { create } from "zustand";

interface SessionState {
  token: string | null;
  user: {
    id: string;
    username: string;
    role: string;
    clearance_level: number;
    departments: string[];
  } | null;
  setAuth: (token: string, user: SessionState["user"]) => void;
  logout: () => void;
  getToken: () => string | null;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  token: typeof window !== "undefined" ? sessionStorage.getItem("access_token") : null,
  user: null,
  setAuth: (token, user) => {
    sessionStorage.setItem("access_token", token);
    set({ token, user });
  },
  logout: () => {
    sessionStorage.removeItem("access_token");
    set({ token: null, user: null });
  },
  getToken: () => get().token,
}));
