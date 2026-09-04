# MEMBER 1 — Frontend / UI Engineer
### SIH26117 · Personal Brief · v1.0

**Read with:** `04_INTEGRATION_CONTRACTS.md §1–3, 6.3` (your contract) and
`03_LLD_STANDARDS.md §1–2, 5` (your rules). You do not need to read the RAG or agent internals.

---

## Your mandate

You build the surface the judges look at for six straight minutes. It must feel like ChatGPT —
instant, streaming, calm — while exposing four things ChatGPT does not: **where the answer came
from**, **how the agent reasoned**, **what the user is allowed to see**, and **proof that nothing
left the building**.

**You own `frontend/` entirely. Nobody else edits it. You edit nothing outside it.**

## Stack (pinned — do not upgrade mid-project)

Next.js `14.2` App Router · TypeScript `5.4` strict · Tailwind `3.4` · shadcn/ui (vendored into
the repo, no CDN) · Framer Motion `11` · Zustand `4.5` · `react-markdown` + `remark-gfm` +
`shiki` · `react-pdf` `9.x` · Recharts `2.12`

**Air-gap rule:** every font, icon, and grammar file is committed to the repo. No
`fonts.googleapis.com`, no icon CDN, no remote asset. `next.config.js` sets
`output: "standalone"` and `NEXT_TELEMETRY_DISABLED=1`.

---

## Phase deliverables

| Phase | Build | Done when |
|---|---|---|
| **P1** | App shell (collapsible history sidebar, message list, auto-resizing composer), login page + JWT storage + guarded route group, light/dark tokens, typed API client generated from M3's OpenAPI into `lib/types.gen.ts` | `npm run build` clean with zero `any`; login → chat shell works against `make mock` |
| **P2** | Documents dashboard (drag-and-drop, per-file progress, MIME icons, status pills, retry). Real SSE streaming with `lib/sse-parser.ts`, blinking cursor, Markdown + GFM tables + Shiki, sticky-bottom autoscroll that yields to the user | 40 MB PDF uploads with live progress; a 600-token answer streams at 60 fps with no jank |
| **P3** | Multimodal composer (paste/drop images, thumbnail strip, remove-before-send, client-side validation). `CitationChip` + `PdfViewer` opening the cited page and highlighting `bbox`. Figure lightbox | Clicking `[3]` opens page 42 with the source paragraph highlighted |
| **P4** | `ReasoningTrace` (live collapsible timeline of `step` frames with per-step timing), route badge with intent + confidence, `SourcesRail` with scores, `ApprovalCard` wired to `/approve`, Recharts trend panel for `DATA_ANALYSIS` | Steps appear live during a 20 s investigator run; denying an approval visibly ends the turn |
| **P5** | `ProofPanel` (EgressMeter, model digest badges, network mode, red breach banner), audit page (filterable table + chain-verify button), role-aware UI that degrades gracefully on `403` and never leaks a restricted title | Auditor sees the audit page, Viewer cannot; proof panel refreshes every 5 s |
| **P6** | Framer Motion polish, skeletons, empty/error/offline states, keyboard shortcuts (`⌘K`, `⌘/`, `Esc`), stop-generation, copy-message, a11y to Lighthouse ≥ 95, responsive to 1280×720 for the projector | Full keyboard-only demo walkthrough; zero console errors; Lighthouse a11y ≥ 95 |

## Your six technical problems

1. **SSE with a Bearer token.** `EventSource` cannot set headers. Use `fetch` + `ReadableStream` +
   `TextDecoder`; write `sse-parser.ts` as a pure function and unit-test it against frames split
   mid-JSON across chunks. This is the bug that eats a whole day if you skip the test.
2. **Streaming Markdown is O(n²).** Re-parsing on every token stutters past ~400 tokens. Buffer
   deltas, flush on a 60 ms rAF tick, memoise completed blocks, re-render only the tail.
3. **Five frame types on one stream.** Model each message as a discriminated union in Zustand so a
   late `step` cannot clobber streamed text.
4. **PDF bbox mapping.** PDF points are bottom-left origin; canvas CSS pixels are top-left. Convert
   through the page viewport scale and handle rotated pages.
5. **Autoscroll that respects the user.** Detect scroll-up, stop pinning, show "jump to latest".
6. **Offline assets.** Verify the production build works with the network physically off, not just
   with `airgap_mode: true` in the API response.

---

## Ready-to-paste AI prompts

Paste the referenced contract section **verbatim** with each prompt. One file per request.

### P1 — App shell

```
You are a senior frontend architect. Stack: Next.js 14.2 App Router, TypeScript strict,
Tailwind 3.4, shadcn/ui (vendored locally — no CDN), Zustand 4.5, Framer Motion 11.
This app is AIR-GAPPED: no remote fonts, no CDN, no telemetry, no external asset.

Create exactly one file: frontend/components/chat/ChatShell.tsx

It renders a ChatGPT-style workbench layout: a collapsible left sidebar of chat sessions
(new-chat button, grouped Today/Yesterday/Older, active highlight), a scrollable main
message area, and a bottom composer. Dark mode via CSS variables (no `dark:` class soup).
Accessible: proper landmarks, aria-labels, visible focus rings, keyboard-reachable sidebar.

CONSTRAINTS
- ≤ 200 lines. If it would be longer, tell me the split and generate only the first file.
- Presentational only: accept data and callbacks via props. No fetching, no business logic.
- Fully typed props interface exported from the same file. No `any`.
- Tailwind utility classes only; no inline styles; no styled-components.
Output the complete file, then 3 lines on what to wire next.
```

### P2 — SSE streaming hook (your highest-risk file)

```
You are a senior frontend engineer. Next.js 14 App Router, TypeScript strict.

Create exactly one file: frontend/hooks/useChatStream.ts

A hook that POSTs a message then consumes an authenticated Server-Sent Events stream via
fetch + ReadableStream (NOT EventSource — we must send an Authorization: Bearer header).

FRAME CONTRACT (exact — do not invent fields):
<paste 04_INTEGRATION_CONTRACTS.md §3 verbatim here>

REQUIREMENTS
- Buffer partial frames: a frame may be split across network chunks at any byte. Only parse
  on a complete "\n\n" boundary. Unit-testable pure parser exported separately as parseSSE().
- Token deltas must NOT trigger a React render per token: accumulate in a ref and flush on a
  ~60 ms requestAnimationFrame tick.
- Handle: route, step, sources, token, approval_required, citations, done, error.
  Ignore unknown event names without throwing.
- Expose { send, stop, isStreaming, message, steps, sources, citations, pendingApproval, error }.
- AbortController for cancellation; clean up on unmount; no state updates after unmount.
- Fully typed with a discriminated union for frames. No `any`.
- ≤ 220 lines. Put the pure parser in frontend/lib/sse-parser.ts if that helps stay under.
Output both files if you split, then 3 lines on what to wire next.
```

### P3 — Citations + PDF highlighting

```
Senior frontend engineer. Next.js 14, TypeScript strict, react-pdf 9.x, Tailwind.

Create exactly one file: frontend/components/docs/PdfViewer.tsx

Props: { documentId: string; page: number; bbox?: [number, number, number, number]; onClose(): void }
It fetches /api/v1/documents/{id}/file with a Bearer token, renders that single page with
react-pdf, and draws a semi-transparent yellow highlight over `bbox`.

CRITICAL: bbox is in PDF user-space points with a BOTTOM-LEFT origin. The canvas overlay is
in CSS pixels with a TOP-LEFT origin. Convert correctly using the page viewport scale, and
handle pages with /Rotate 90 or 270.

Also: page navigation, zoom, loading skeleton, error state, Esc to close, focus trap.
≤ 250 lines, fully typed, no `any`. Output the file plus 3 lines on wiring.
```

### P4 — Reasoning trace + approval card

```
Senior frontend engineer. Next.js 14, TypeScript strict, Tailwind, Framer Motion 11.

Create exactly one file: frontend/components/chat/ReasoningTrace.tsx

Renders a live, collapsible agent reasoning timeline from an array of steps:
<paste the `step` frame schema from 04_INTEGRATION_CONTRACTS.md §3 verbatim>

- Vertical timeline; one row per step; icon per phase (plan/reason/act/observe/reflect/synthesize).
- Show tool name and a compact argument preview for `act` steps; elapsed_ms per step.
- Collapsed by default showing "Reasoned for 6 steps · 18.4 s"; expands with a Framer Motion
  height animation.
- While streaming, the newest step has a subtle pulse; new rows animate in without shifting
  the message below (reserve height).
- Accessible: <ol>, aria-expanded on the toggle, respects prefers-reduced-motion.
≤ 200 lines, fully typed, no `any`. Then generate ApprovalCard.tsx in a SEPARATE request.
```

### P5 — Sovereignty proof panel

```
Senior frontend engineer. Next.js 14, TypeScript strict, Tailwind, Framer Motion.

Create exactly one file: frontend/components/sovereignty/ProofPanel.tsx

Polls GET /api/v1/sovereignty/status every 5 s and renders a compact "sovereignty dashboard"
that a judge can read from three metres away:
<paste 04_INTEGRATION_CONTRACTS.md §6.3 verbatim>

- Hero metric: "0 BYTES EGRESSED" large, monospace, green.
- Secondary: outbound attempts blocked (animated counter), network mode, DNS resolvable = false.
- Model badges: role, name, truncated digest, a "local" chip.
- If `breach` is non-null: full-width red banner, alert role, aria-live="assertive".
- Uptime as a human string. Skeleton on first load. Retry on fetch failure with backoff.
≤ 200 lines, fully typed, no `any`. This component is on screen during the pitch — make the
typography and spacing deliberate, not default.
```

---

## Contracts you must honour exactly

- `04_INTEGRATION_CONTRACTS.md §2` — every endpoint, request body, and response shape
- `04_INTEGRATION_CONTRACTS.md §3` — **the SSE frame schema.** Copy field names character for
  character. The `sources` frame carries `page_start`/`page_end` only — it has **no bbox
  field** (`bbox_union` lives only in the internal Qdrant payload, §5, and never reaches the
  browser). The `citations` frame is the only place you get a `bbox` to draw a highlight from.
  Do not build `SourcesRail` expecting a box to draw; it can only ever show a page number.
- `04_INTEGRATION_CONTRACTS.md §6.3` — sovereignty status
- `lib/types.gen.ts` is **generated** from M3's OpenAPI (`make types`). Never hand-edit it.

## Security rules that apply to you

- The frontend is **not** a filter. Never rely on hiding a UI element for security; the API
  already enforces access. But also never render a restricted document title you received by
  accident — report it to M3 as a bug immediately.
- Never log tokens or document content to the console, including in dev builds.
- Store the access token in memory + `sessionStorage`; never in `localStorage`.
- Render Markdown with HTML disabled. Retrieved document text is untrusted input.

## Your definition of done, every phase

```
□ Runs against docker compose (not just `next dev` on your machine)
□ ≤ 300 LOC per file, ≤ 200 for components
□ tsc --strict clean, zero `any`
□ Works with the mock server AND the real API
□ Keyboard accessible, visible focus, aria labels present
□ No remote asset of any kind (grep for "https://" in the build output)
□ No console errors or React key warnings
□ Reviewed by M3
```


