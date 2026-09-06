const NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

/**
 * API base for browser calls.
 * - Container image bakes this as "" (same-origin): the Next server proxies
 *   /api/* to the API container over the internal appnet — the only egress
 *   surface in airgapped mode is the web server.
 * - Bare-metal dev (env unset at build) falls back to the direct API host.
 */
export const API_BASE =
  typeof NEXT_PUBLIC_API_URL === "undefined" ? "http://localhost:8000" : NEXT_PUBLIC_API_URL;