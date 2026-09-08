# MEMBER 3 — Backend & Security Engineer
### SIH26117 · Personal Brief · v1.0

**Read with:** all of `04_INTEGRATION_CONTRACTS.md` (you are its author),
`01_ALGORITHMS.md §3` (your algorithm), `03_LLD_STANDARDS.md` (all of it).

---

## Your mandate

Two jobs, both critical. First, you author and publish the contract every other member codes
against — **your frozen OpenAPI schema and mock server on Day 2 is the single most
schedule-critical artefact in this project.** Second, you own the security story that actually
wins this problem statement: RBAC that filters *before* retrieval, and an audit log that cannot
be rewritten.

**You own:** `backend/main.py`, `api/`, `core/`, `db/`, `schemas/`, `services/{crypto,audit}/`,
`tests/security/`.

---

## Phase deliverables

| Phase | Build | Done when |
|---|---|---|
| **P1** | FastAPI skeleton (`main.py` mounts routers only, < 60 LOC). Async SQLAlchemy 2.0 + asyncpg + Alembic; all tables from `§4` of the contracts. RS256 JWT (15-min access, rotating refresh), bcrypt cost 12, login lockout. `Depends()` chain. **Publish and freeze `openapi.json` + `make mock`.** RFC 9457 error handler | `alembic upgrade head` from scratch; login returns a valid JWT; mock serves every P2 endpoint |
| **P2** | `POST /documents` (libmagic sniffing, 200 MB cap, SHA-256 dedupe, AES-256-GCM envelope encryption, `202` + ARQ enqueue). `GET /documents` paginated + ACL-filtered. `GET /documents/{id}/file` with `Range`. Chat CRUD. **SSE endpoint** with the frozen frame contract, 15 s heartbeats, disconnect cleanup. `structlog` + `correlation_id` middleware | 40 MB upload ACKs in < 500 ms; SSE streams from a stub without leaking tasks |
| **P3** | Attachments (image upload, ownership checks, thumbnails, short-lived local URLs). Ingest progress SSE fan-out from Redis pub/sub. Dead-letter table + retry endpoint. `slowapi` per-user rate limiting | M1 shows live ingest progress; a failed doc shows a reason and retries |
| **P4** | Agent plumbing for M5: `POST /messages` invoking the graph, `POST /approve` resuming from the checkpointer, `GET /state`. LangGraph `AsyncPostgresSaver` tables via Alembic. 60 s `asyncio.timeout` with graceful cancellation that still writes an audit row | Approve/deny resumes the graph; closing the browser mid-stream leaves no zombie generation |
| **P5** | **`core/rbac.py`** (lattice, roles, `can_read()`, `require_clearance`). `build_acl_filter()` + `acl_reverify()` with M4. Audited re-label endpoint. **Hash-chained audit writer**, `GET /audit`, `GET /audit/verify`, Postgres `DO INSTEAD NOTHING` rules + privilege revocation. The full `tests/security/` matrix | 200 adversarial prompts → 0 leaks; chain verifies; `UPDATE audit_log` changes nothing |
| **P6** | Pooling (`pool_size=20`), identity-scoped retrieval cache, `EXPLAIN ANALYZE` + indexes on hot queries, gzip for JSON only (never SSE), health/readiness probes, DB backup/restore script, final API docs | p95 non-LLM latency < 120 ms; `make backup && make restore` round-trips |

## Your six technical problems

1. **SSE done properly.** Async generator, `media_type="text/event-stream"`,
   `X-Accel-Buffering: no`, `: keep-alive` every 15 s, and `await request.is_disconnected()` →
   cancel the graph task. Skip that last part and every abandoned tab leaks an Ollama generation
   until the GPU is full — which will happen during the demo, not before it.
2. **Async purity.** One `AsyncSession` per request via `Depends`; never share across tasks. Route
   `bcrypt`, `libmagic`, `PyMuPDF` through `run_in_threadpool` or streaming visibly stutters.
3. **Cache keys must include identity.** A retrieval cache keyed only on the prompt is a
   cross-clearance leak. Key on `(prompt_hash, clearance_level, sorted(departments))`.
4. **Hash-chain concurrency.** Two concurrent appends can read the same `prev_hash` and fork the
   chain. Serialise on a single-row `audit_chain_head` with `SELECT … FOR UPDATE`.
5. **Fail closed, always.** Missing claim, unparseable label, Qdrant unreachable → deny. Never
   default to allow, never default to `PUBLIC`.
6. **Audit under cancellation.** Write the audit row in a `finally` block so a cancelled or
   errored turn is still recorded. "No audit row" must never be a way to hide an action.

---

## Ready-to-paste AI prompts

### P1 — Auth + JWT

```
You are a senior backend security engineer. Stack: FastAPI 0.111, Pydantic 2.7,
SQLAlchemy 2.0 async + asyncpg, python-jose[cryptography], passlib[bcrypt], Python 3.11.
This system is AIR-GAPPED: no external identity provider, no outbound network calls.

Create exactly one file: backend/core/security.py  (≤ 200 lines)

REQUIREMENTS
- RS256 JWT signing with a local keypair loaded from settings.jwt_private_key_path.
  Include a `kid` header so keys can rotate. Generate the keypair on first boot if absent.
- Access token TTL 15 min with claims: sub, role, clearance_level, departments[], jti, iat, exp.
- Opaque refresh tokens: random 32 bytes, only the hash stored, single-use rotating, 8 h TTL.
- bcrypt cost 12. verify_password() must be constant-time and must run a dummy verify when
  the user does not exist, so timing cannot enumerate usernames.
- Lockout after 5 failed attempts for 15 min.
- decode_access_token() raises typed AegisError subclasses (never HTTPException — this is
  core/, not api/).

CONSTRAINTS
- Import `settings` from core.config; never call os.getenv.
- Every function fully type-annotated with a docstring.
- bcrypt is blocking: expose async wrappers using starlette.concurrency.run_in_threadpool.
- No secret, hash, or token value may appear in any log line.
Output the complete file, then 3 lines on what to wire next.
```

### P2 — SSE endpoint (highest-risk backend file)

```
Senior FastAPI engineer. FastAPI 0.111, Python 3.11 async.

Create exactly one file: backend/api/v1/chat_stream.py  (≤ 200 lines)

A GET /chat/sessions/{session_id}/stream?turn_id=... Server-Sent Events endpoint.

EXACT FRAME CONTRACT (do not invent fields, do not rename anything):
<paste 04_INTEGRATION_CONTRACTS.md §3 verbatim>

REQUIREMENTS
- StreamingResponse with media_type="text/event-stream" and headers
  Cache-Control: no-cache, Connection: keep-alive, X-Accel-Buffering: no.
- Async generator consuming an asyncio.Queue that the agent runtime publishes to.
- Emit a ": keep-alive\n\n" comment every 15 s so proxies do not close the stream.
- Poll `await request.is_disconnected()`; on disconnect, CANCEL the agent task. A leaked
  Ollama generation per abandoned tab is unacceptable.
- Wrap the whole turn in `async with asyncio.timeout(settings.turn_deadline_s)`; on timeout
  emit an `error` frame with code "deadline_exceeded".
- In a `finally` block: always write the audit row (even on cancellation or error) and always
  drain/close the queue.
- Thin controller: no prompt building, no retrieval. Delegate to ChatService via Depends.
Output the complete file, then 3 lines on what to wire next.
```

### P5 — RBAC decision function

```
Senior backend security engineer. FastAPI 0.111, Pydantic 2.7, qdrant-client 1.9.

Create exactly one file: backend/core/rbac.py  (≤ 180 lines)

Implement a clearance-lattice + department-compartment access model:

  Clearance(IntEnum): PUBLIC=0, INTERNAL=1, CONFIDENTIAL=2, RESTRICTED=3
  Role(StrEnum): VIEWER, ANALYST, ENGINEER, AUDITOR, ADMIN
  MAX_CLEARANCE per role: VIEWER 0, ANALYST 1, ENGINEER 2, AUDITOR 3, ADMIN 3
  CROSS_DEPARTMENT = {AUDITOR, ADMIN}   # only these ignore compartments

Provide:
1. ServerUserContext (frozen Pydantic model) built ONLY from verified JWT claims.
2. can_read(user, doc_labels) -> Decision  — allow/deny with a machine-readable reason.
   BOTH conditions must hold: doc.clearance_level <= user.clearance_level AND
   (doc.department in user.departments OR user.role in CROSS_DEPARTMENT).
   Also deny when status != READY, and when legal_hold is set and role != AUDITOR.
3. build_acl_filter(user) -> qdrant_client.models.Filter — a PRE-FILTER with `must`
   conditions on clearance_level (Range lte), status == READY, and department MatchAny.
4. FastAPI dependencies require_role(*roles) and require_clearance(level).

CRITICAL CONSTRAINTS
- FAIL CLOSED: any missing, malformed, or unknown value denies access.
- No function may accept a client-supplied filter, clearance, or department. There must be
  no code path by which a caller can widen its own access.
- Pure and synchronous (no I/O) so it is trivially unit-testable.
- Raise AegisError subclasses, never HTTPException — this is core/.
Also write backend/tests/unit/test_rbac.py covering: equal clearance + wrong department
denied; AUDITOR cross-department allowed; VIEWER blocked from clearance 1; unknown role
denied; legal_hold respected.
```

### P5 — Hash-chained audit log

```
Senior backend engineer. SQLAlchemy 2.0 async, PostgreSQL 16, Python 3.11.

Create exactly one file: backend/services/audit/writer.py  (≤ 180 lines)

An append-only, tamper-evident audit log.

- Canonical serialisation: json.dumps(entry, sort_keys=True, separators=(",",":")).
- entry_hash = sha256(f"{prev_hash}|{canonical_body}").
- prev_hash comes from a single-row `audit_chain_head` table read with SELECT ... FOR UPDATE
  inside the same transaction, so CONCURRENT APPENDS CANNOT FORK THE CHAIN. This is the
  requirement most implementations get wrong — get it right.
- append(session, entry) returns the created row; update audit_chain_head in the same txn.
- verify_chain(session, from_id=None) walks the chain and returns
  {valid, entries, first_break_id, anchor}.
- Emit-and-forget helper emit(action, user, **fields) that never raises into the request path
  (log the failure instead) — a broken audit write must not take down a query, but it MUST be
  loudly logged and counted in a metric.
- Redact: never store passwords, tokens, DEKs, or raw document text. Store prompt_hash, not
  the prompt body, when the prompt may contain confidential content.

Also emit the Alembic migration adding:
  CREATE RULE audit_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
  CREATE RULE audit_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;
  REVOKE UPDATE, DELETE ON audit_log FROM aegis_app;
```

---

## Contracts you author and must not break silently

You are the owner of `04_INTEGRATION_CONTRACTS.md`. Once it is frozen at the end of Day 2, any
change goes through the CCR process in §8 — including changes you personally think are obvious
improvements. Four other members will already have code written against v1.0.

Your Day-2 checklist:

```
□ openapi.json committed and published to the team
□ `make mock` runs and serves every §2 endpoint with realistic fixtures
□ Mock SSE stream emits the full §3 frame sequence with realistic delays
□ Scenario query params: ?scenario=approval and ?scenario=denied both work
□ `make types` regenerates M1's lib/types.gen.ts from the schema
□ Every member has confirmed in writing that they can build against it
```

## Security rules you enforce for the whole team

You are the last line of defence on rules S1–S10 in `03_LLD_STANDARDS.md §4`. In particular, you
review every PR that touches retrieval for one thing: **is `build_acl_filter()` on that path?**

Your test matrix (all must pass before P5 closes):

```
□ test_rbac_leakage.py           200 adversarial prompts → 0 unauthorised document_ids
□ test_prefilter_not_postfilter  mock Qdrant asserts query_filter non-empty on EVERY search
□ test_stale_payload.py          re-classified doc dropped by acl_reverify + SECURITY_ANOMALY
□ test_audit_immutable.py        UPDATE/DELETE change nothing; chain still verifies
□ test_audit_concurrent.py       50 parallel appends produce one unbroken chain
□ test_jwt_tamper.py             modified clearance claim → 401
□ test_filter_injection.py       client-sent clearance/filter/department fields are ignored
□ test_no_egress.py              api and worker cannot reach 1.1.1.1:53 or huggingface.co:443
□ test_upload_validation.py      renamed .exe, zip bomb, 300 MB file, path traversal all rejected
```

## Your definition of done, every phase

```
□ Runs inside docker compose
□ ≤ 300 LOC per file; main.py under 60; no logic in api/
□ mypy clean; every boundary is a Pydantic model
□ AegisError subclasses only; HTTPException confined to api/
□ Alembic migration written and reversible
□ Audit event emitted for every state change and every data read
□ structlog entry with correlation_id at every entry point
□ Unit + integration tests passing; CI green
□ Reviewed by M4 (data paths) or M1 (API shape)
```



