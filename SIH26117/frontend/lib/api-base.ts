/**
 * API base for browser calls. Same-origin by default: the deployment proxies
 * /api/* to the API container over the internal appnet (nginx in the web image,
 * or the Next rewrite in dev) — the only egress surface in airgapped mode is
 * the web server. A direct-host dev image sets NEXT_PUBLIC_API_URL to the API
 * base URL at build time.
 */
export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";