"use client";

import { create } from "zustand";
import {
  TOKEN_KEY,
  USER_KEY,
  getStoredUser,
  getStoredToken,
  clearStoredAuth,
  storeStoredAuth,
} from "@/lib/api-client";

interface SessionUser {
  id: string;
  username: string;
  role: string;
  clearance_level: number;
  departments: string[];
}

interface SessionState {
  token: string | null;
  user: SessionUser | null;
  setAuth: (token: string, user: SessionUser) => void;
  logout: () => void;
  getToken: () => string | null;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  token:
    typeof window !== "undefined"
      ? getStoredToken()
      : null,
  user: typeof window !== "undefined" ? getStoredUser<SessionUser>() : null,
  setAuth: (token, user) => {
    storeStoredAuth(token, user);
    set({ token, user });
  },
  logout: () => {
    clearStoredAuth();
    set({ token: null, user: null });
  },
  getToken: () => get().token,
}));