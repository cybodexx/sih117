"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, type Variants } from "framer-motion";
import { useSessionStore } from "@/store/sessionStore";
import { API_BASE } from "@/lib/api-base";
import { BrandEmblem } from "@/components/BrandEmblem";

const EASE = [0.16, 1, 0.3, 1] as const;

const revealLine = (delay: number): Variants => ({
  hidden: { y: "65%" },
  show: {
    y: "0%",
    transition: { duration: 1.0, ease: EASE, delay },
  },
});

const fadeUp = (delay: number): Variants => ({
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.9, ease: EASE, delay },
  },
});

const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.9 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.7, ease: EASE, delay: 0.2 },
  },
};

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Login failed" }));
        setError(data.detail || "Login failed");
        setLoading(false);
        return;
      }
      const data = await res.json();
      useSessionStore.getState().setAuth(data.access_token, data.user);
      router.push("/chat/new");
    } catch {
      setError("Connection failed. Is the backend running?");
      setLoading(false);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black px-4">
      <motion.div
        initial="hidden"
        animate="show"
        className="relative z-10 flex w-full max-w-[520px] flex-col items-center"
      >
        {/* Badge */}
        <motion.div variants={popIn} className="mb-9 flex justify-center">
          <span className="metal-pill inline-flex items-center gap-2 rounded-[5px] px-3.5 py-[9px] text-[12.5px] tracking-tight text-gray-200">
            <svg
              className="h-[18px] w-5"
              viewBox="0 0 24 24"
              fill="white"
              style={{ filter: "drop-shadow(0 0 3px rgba(255,255,255,0.45))" }}
            >
              <path d="M12 2.6C12.55 2.6 12.88 3.15 13.08 4.7c.62 4.7 1.52 5.6 6.22 6.22 1.55.2 2.1.53 2.1 1.08s-.55.88-2.1 1.08c-4.7.62-5.6 1.52-6.22 6.22-.2 1.55-.53 2.1-1.08 2.1s-.88-.55-1.08-2.1c-.62-4.7-1.52-5.6-6.22-6.22C3.15 12.88 2.6 12.55 2.6 12s.55-.88 2.1-1.08c4.7-.62 5.6-1.52 6.22-6.22C11.12 3.15 11.45 2.6 12 2.6Z" />
            </svg>
            AEGIS-WB — Operational AI Infrastructure
          </span>
        </motion.div>

        {/* Mark */}
        <motion.div
          variants={{
            hidden: { opacity: 0, scale: 0.85 },
            show: {
              opacity: 1,
              scale: 1,
              transition: { duration: 0.9, ease: EASE, delay: 0.42 },
            },
          }}
        >
          <BrandEmblem size="lg" className="mb-9" />
        </motion.div>

        {/* Headline */}
        <h1 className="text-center text-[38px] font-medium leading-[1.08] tracking-[-0.04em] text-white md:text-[44px]">
          <span className="block overflow-hidden px-2 pb-[0.14em] pt-[0.06em]">
            <motion.span variants={revealLine(0.6)} className="block">
              Command your
            </motion.span>
          </span>
          <span className="block overflow-hidden px-2 pb-[0.14em] pt-[0.06em]">
            <motion.span variants={revealLine(0.82)} className="block">
              industrial{" "}
              <em className="serif-accent text-[1.08em] text-white/60">
                data.
              </em>
            </motion.span>
          </span>
        </h1>

        <motion.p
          variants={fadeUp(1.02)}
          className="mt-[18px] max-w-[400px] text-center text-[15.5px] leading-[1.55] tracking-[-0.015em] text-white/55"
        >
          Sign in to your sovereign, air-gapped AI workbench. Nothing leaves
          this machine.
        </motion.p>

        {/* Form */}
        <motion.form
          onSubmit={handleLogin}
          variants={fadeUp(1.18)}
          className="mt-9 w-full max-w-[360px] space-y-3"
        >
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-lg border border-red-400/25 bg-red-500/10 px-3 py-2.5 text-sm text-red-300"
            >
              <svg className="mt-0.5 h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}
          <input
            id="username"
            type="text"
            placeholder="Username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="h-[46px] w-full rounded-[8px] border border-white/15 bg-white/[0.04] px-4 text-[15px] tracking-[-0.01em] text-white placeholder:text-white/40 transition-colors focus:border-white/40 focus:outline-none focus:bg-white/[0.07]"
            required
            autoFocus
          />
          <input
            id="password"
            type="password"
            placeholder="Password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="h-[46px] w-full rounded-[8px] border border-white/15 bg-white/[0.04] px-4 text-[15px] tracking-[-0.01em] text-white placeholder:text-white/40 transition-colors focus:border-white/40 focus:outline-none focus:bg-white/[0.07]"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="liquid-btn-solid mt-1 h-[46px] w-full cursor-pointer rounded-[8px] text-[14px] font-medium tracking-tight disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </motion.form>

        {/* Footer line */}
        <motion.p
          variants={fadeUp(1.32)}
          className="mt-7 flex items-center gap-1.5 text-[12px] tracking-[-0.01em] text-white/40"
        >
          <svg className="h-3.5 w-3.5 text-emerald-400/80" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Air-gapped · Local inference · Zero egress
        </motion.p>
      </motion.div>
    </main>
  );
}