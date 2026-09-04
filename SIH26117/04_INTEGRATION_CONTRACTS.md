# SIH26117 — Integration Contracts (FROZEN)
### v1.0 · frozen end of Day 2 · changes only via a CCR (§8)

> **Read this before writing a single line of code.** These are the only interfaces that cross
> member boundaries. Six people can build in parallel *precisely because* these are fixed. If you
> paraphrase a field name from memory instead of copying it from here, you will discover the
> mismatch on Day 17 — the most expensive possible time.
>
> **Signed off by:** M1 ☐ M2 ☐ M3 ☐ M4 ☐ M5 ☐ M6 ☐

---

## 1. Common Types

```ts
type UUID = string;              // canonical lowercase hyphenated
type ISODateTime = string;       // RFC 3339 UTC, e.g. "2026-09-04T10:12:33Z"

type Role = "VIEWER" | "ANALYST" | "ENGINEER" | "AUDITOR" | "ADMIN";
type Clearance = 0 | 1 | 2 | 3;  // PUBLIC | INTERNAL | CONFIDENTIAL | RESTRICTED
type DocStatus = "QUEUED" | "PARSING" | "EMBEDDING" | "READY" | "FAILED";
type ChunkType = "TEXT" | "TABLE" | "FIGURE" | "IMAGE_DESC" | "IMAGE_OCR"
               | "DATA_CARD" | "DATA_SLICE" | "OCR_NOTE";
type Intent = "DOC_QA" | "VISION" | "DATA_ANALYSIS" | "INCIDENT" | "COMPLIANCE" | "CHITCHAT";
type Department = "MAINTENANCE" | "OPERATIONS" | "SAFETY" | "QUALITY" | "ENGINEERING" | "ADMIN";
```

**Error envelope — every non-2xx response, no exceptions:**

```json
{
  "type": "/errors/clearance_denied",
  "title": "Insufficient clearance",
  "status": 403,
  "detail": "This document requires RESTRICTED clearance.",
  "correlation_id": "01J8XQ7YV3K2M9NF5T1WZBQ4RD"
}
```

Content type: `application/problem+json`. `correlation_id` is echoed in the
`X-Correlation-ID` response header on **every** response, success or failure.

---

## 2. REST API (owner M3 · base path `/api/v1`)

### 2.1 Auth

| Method | Path | Body → Response | Roles |
|---|---|---|---|
| `POST` | `/auth/login` | `{username, password}` → `{access_token, refresh_token, token_type:"bearer", expires_in:900, user}` | public |
| `POST` | `/auth/refresh` | `{refresh_token}` → same shape (refresh rotates) | public |
| `POST` | `/auth/logout` | `{}` → `204` | any |
| `GET` | `/auth/me` | → `UserRead` | any |

```json
// UserRead
{"id":"uuid","username":"r.sharma","full_name":"R. Sharma","role":"ENGINEER",
 "clearance_level":2,"departments":["MAINTENANCE","OPERATIONS"],"created_at":"…"}
```

### 2.2 Documents

| Method | Path | Notes | Roles |
|---|---|---|---|
| `POST` | `/documents` | `multipart/form-data`: `file`, optional `department`, optional `clearance_level` (**ignored unless ADMIN**) → `202 DocumentAccepted` | ENGINEER, ANALYST, ADMIN |
| `GET` | `/documents` | `?status=&department=&q=&page=1&size=20` → `Page<DocumentRead>` — **ACL-filtered server-side** | any |
| `GET` | `/documents/{id}` | → `DocumentRead` · `403` if not permitted | any |
| `GET` | `/documents/{id}/file` | streams decrypted bytes, supports `Range` (required by the PDF viewer) | any (ACL) |
| `GET` | `/documents/{id}/thumbnail` | → `image/webp` | any (ACL) |
| `POST` | `/documents/{id}/retry` | re-enqueue a `FAILED` document | ENGINEER, ADMIN |
| `PATCH` | `/documents/{id}/labels` | `{clearance_level, department}` → audited re-label + re-index | ADMIN |
| `DELETE` | `/documents/{id}` | crypto-shred + purge vectors | ADMIN |

```json
// DocumentAccepted (202)
{"document_id":"uuid","status":"QUEUED","checksum":"sha256:…","deduplicated":false}

// DocumentRead
{"id":"uuid","filename":"turbine_om_manual.pdf","mime":"application/pdf",
 "size_bytes":18234112,"page_count":214,"status":"READY","chunk_count":412,
 "clearance_level":2,"department":"MAINTENANCE","owner_id":"uuid",
 "checksum":"sha256:…","error_reason":null,
 "created_at":"…","ingested_at":"…"}
```

### 2.3 Chat

| Method | Path | Notes |
|---|---|---|
| `POST` | `/chat/sessions` | `{title?}` → `ChatSessionRead` |
| `GET` | `/chat/sessions` | `?page=&size=` → `Page<ChatSessionRead>` |
| `GET` | `/chat/sessions/{id}/messages` | → `MessageRead[]` (full history with citations) |
| `DELETE` | `/chat/sessions/{id}` | `204` |
| `POST` | `/chat/sessions/{id}/messages` | `MessageCreate` → `202 {message_id, turn_id}` — starts the agent run |
| `GET` | `/chat/sessions/{id}/stream?turn_id=` | **SSE** (§3) |
| `POST` | `/chat/sessions/{id}/approve` | `{approval_id, decision:"APPROVED"\|"DENIED", note?}` → `202` — resumes the graph |
| `POST` | `/chat/sessions/{id}/stop` | cancels the in-flight turn → `204` |

```json
// MessageCreate
{"content":"Why did Turbine-4 trip on 14 Aug?","attachment_ids":["uuid"]}
// NOTE: the client MUST NOT send clearance, department, filters, or document ids to
// scope retrieval. Any such field is ignored by the server. (See §7 rule C1.)

// MessageRead
{"id":"uuid","turn_id":"uuid","role":"assistant","content":"…markdown…",
 "intent":"INCIDENT","route_confidence":0.91,"grounded":true,"abstained":false,
 "citations":[Citation],"reasoning":[ReasoningStep],"sources":[SourceRef],
 "tokens_in":4210,"tokens_out":386,"latency_ms":18422,"created_at":"…"}
```

### 2.4 Audit, admin, sovereignty

| Method | Path | Notes | Roles |
|---|---|---|---|
| `GET` | `/audit` | `?action=&user_id=&from=&to=&page=` → `Page<AuditRead>` | AUDITOR, ADMIN |
| `GET` | `/audit/verify` | → `{valid, entries, first_break, anchor}` | AUDITOR, ADMIN |
| `GET` | `/audit/export` | signed NDJSON download | AUDITOR |
| `GET` | `/sovereignty/status` | → `SovereigntyStatus` (§6) | any |
| `GET` | `/admin/users` · `POST` `/admin/users` · `PATCH` `/admin/users/{id}` | user + clearance management (audited) | ADMIN |
| `GET` | `/health` · `GET` `/ready` | liveness / readiness (checks PG, Qdrant, Ollama) | public |

---

## 3. SSE Streaming Contract (M1 ↔ M3 ↔ M5) — **the most important contract in the project**

Transport: `text/event-stream`, headers `Cache-Control: no-cache`, `Connection: keep-alive`,
`X-Accel-Buffering: no`. Every frame is `event: <name>` + `data: <one-line JSON>`.
A `: keep-alive` comment is sent every 15 s.

**Guaranteed frame order per turn:**

```
route  →  step*  →  [approval_required  →  (resume)]  →  sources  →  token*  →  citations  →  done
                                                                     └─ or ─→ error
```

```jsonc
// event: route            — which agent was chosen (M1 renders the route badge)
{"intent":"INCIDENT","confidence":0.91,"rationale":"root-cause question with a date",
 "sub_queries":["Turbine-4 alarms around 2026-08-14","vibration trend before the trip"]}

// event: step             — one reasoning step (M1 appends to the live trace)
{"seq":3,"phase":"act","label":"Searching maintenance manuals",
 "tool":"vector_search","tool_args":{"query":"turbine trip protection threshold"},
 "detail":null,"elapsed_ms":812}
// phase ∈ "plan" | "reason" | "act" | "observe" | "reflect" | "synthesize"

// event: sources          — the retrieved, ACL-approved, reranked chunks (M1's sources rail)
{"sources":[{"n":1,"chunk_id":"uuid","document_id":"uuid",
             "document_title":"Turbine O&M Manual Rev-C","page_start":42,"page_end":42,
             "score":0.87,"chunk_type":"TEXT","suspected_injection":false,
             "snippet":"Protection trips at vibration > 7.1 mm/s RMS …"}]}

// event: token            — one streamed delta (many per turn)
{"delta":"The trip was caused by "}

// event: approval_required — the graph is PAUSED at hitl_gate
{"approval_id":"uuid","tool":"delete_document","risk":"HIGH",
 "arguments":{"document_id":"uuid","filename":"incident_T4_2026-08-14.pdf"},
 "rationale":"The user asked me to remove the incident file.",
 "expires_at":"2026-09-04T10:20:00Z"}

// event: citations        — final resolved citations, indices match the [n] markers in the text
{"citations":[{"n":1,"document_id":"uuid","document_title":"Turbine O&M Manual Rev-C",
               "page":42,"bbox":[72.0,118.5,523.0,402.25],
               "snippet":"Protection trips at vibration > 7.1 mm/s RMS …"}]}

// event: done
{"message_id":"uuid","turn_id":"uuid","grounded":true,"abstained":false,
 "citation_coverage":0.94,"tokens_in":4210,"tokens_out":386,
 "latency_ms":18422,"tool_calls":5}

// event: error            — terminal; M1 shows a retry affordance
{"code":"model_unavailable","message":"The local model runtime did not respond.",
 "retryable":true,"correlation_id":"01J…"}

// event: ingest_progress  — sent on the documents stream, not the chat stream
{"document_id":"uuid","status":"EMBEDDING","progress":0.62,
 "pages_done":132,"pages_total":214,"chunks":248}
```

**Client rules (M1):** frames may split across TCP chunks — buffer until `\n\n`. Ignore unknown
`event:` names rather than throwing. Treat `done` and `error` as terminal and close the reader.
Never assume `sources` arrives before the first `token` for *streamed* rendering purposes; assume
only the documented order.

---

## 4. PostgreSQL Schema (owner M3 — column names are contractual)

```sql
users(id uuid pk, username citext unique, full_name text, password_hash text,
      role text, clearance_level smallint, departments text[],
      is_active bool, failed_attempts int, locked_until timestamptz, created_at timestamptz)

documents(id uuid pk, owner_id uuid fk users, filename text, mime text,
          size_bytes bigint, page_count int, checksum text unique,
          storage_key text, wrapped_dek bytea,
          clearance_level smallint, department text, legal_hold bool default false,
          status text, error_reason text, chunk_count int,
          created_at timestamptz, ingested_at timestamptz)
          -- INDEX (status), (department, clearance_level), (checksum)

chunk_refs(id uuid pk,               -- SAME id as the Qdrant point id (uuid5)
           document_id uuid fk documents on delete cascade,
           chunk_index int, chunk_type text, page_start int, page_end int,
           bbox jsonb, heading_path text[], token_count int, text_preview text,
           suspected_injection bool default false)
           -- UNIQUE (document_id, chunk_index)

datasets(id uuid pk, document_id uuid fk documents, table_name text unique,
         row_count int, schema_json jsonb, created_at timestamptz)

chat_sessions(id uuid pk, user_id uuid fk users, title text,
              created_at timestamptz, updated_at timestamptz)

chat_messages(id uuid pk, session_id uuid fk chat_sessions on delete cascade,
              turn_id uuid, role text, content text,
              intent text, route_confidence real, grounded bool, abstained bool,
              citations jsonb, reasoning jsonb, sources jsonb,
              tokens_in int, tokens_out int, latency_ms int, created_at timestamptz)

approvals(id uuid pk, session_id uuid fk, turn_id uuid, tool text, risk text,
          arguments jsonb, decision text, decided_by uuid fk users,
          note text, requested_at timestamptz, decided_at timestamptz)

audit_log(id bigserial pk, ts timestamptz default now(),
          user_id uuid, role text, clearance_at_time smallint,
          action text, resource_type text, resource_id text,
          route text, intent text, tool_calls jsonb, document_ids uuid[],
          prompt_hash text, decision text, severity text,
          ip inet, user_agent text, correlation_id text,
          prev_hash text not null, entry_hash text not null unique)
          -- RULES: no UPDATE, no DELETE (see 01_ALGORITHMS.md §3.6)

audit_chain_head(id int pk check (id = 1), last_hash text)   -- row lock for serialised appends

checkpoints / checkpoint_writes                              -- created by LangGraph's saver
```

---

## 5. Qdrant Contract (owner M4)

```
Collection            : aegis_bge_m3_1024
Dense vector          : name="dense", size=1024, distance=Cosine
Sparse vector         : name="bm25"
Point id              : uuid5(NAMESPACE_OID, f"{document_id}:{chunk_index}")   ← deterministic
Quantization          : scalar int8, always_ram=true
Payload indexes (MUST): clearance_level:integer, department:keyword,
                        document_id:uuid, status:keyword, chunk_type:keyword, page_start:integer
```

```jsonc
// Payload — every field is required; M5 and M1 both read these names
{
  "text": "verbatim chunk text",
  "document_id": "uuid",
  "document_title": "Turbine O&M Manual Rev-C",
  "chunk_index": 42,
  "chunk_type": "TEXT",
  "heading_path": ["Ch 4 Maintenance", "4.2 Bearing Lubrication"],
  "page_start": 42, "page_end": 43,
  "bbox_union": [72.0, 118.5, 523.0, 402.25],
  "token_count": 498,
  "clearance_level": 2,          // ← ACL. Copied from documents.clearance_level at ingest.
  "department": "MAINTENANCE",   // ← ACL.
  "status": "READY",
  "suspected_injection": false,
  "checksum": "sha256:…",
  "ingested_at": "2026-09-04T10:12:33Z"
}
```

---

## 6. Internal Interfaces

### 6.1 Retrieval tool signature (M4 → M5) — note what is *absent*

```python
# services/rag/retriever.py — the ONLY public retrieval entry point
async def search(
    query: str,
    acl: models.Filter,          # built by build_acl_filter(user_ctx). NOT caller-authored.
    *,
    k: int = 20,
    doc_ids: list[UUID] | None = None,   # narrowing only; can never widen the ACL
    chunk_types: list[ChunkType] | None = None,
) -> list[RetrievedChunk]: ...

class RetrievedChunk(BaseModel):
    chunk_id: UUID; document_id: UUID; document_title: str
    text: str; score: float; chunk_type: ChunkType
    page_start: int; page_end: int; bbox: list[float] | None
    heading_path: list[str]; suspected_injection: bool
```

There is **no `filter` parameter and no `clearance` parameter**. A tool cannot widen its own
access because the API to do so does not exist. This is the design, not an oversight.

### 6.2 LLM client (M6 → M4, M5)

```python
# services/llm/ollama_client.py — the single LLM entry point for the whole codebase
class OllamaClient:
    async def chat(self, messages: list[Msg], *, model: str | None = None,
                   temperature: float = 0.2, max_tokens: int = 1024,
                   timeout_s: float = 60.0) -> str: ...
    async def stream(self, messages: list[Msg], **kw) -> AsyncIterator[str]: ...
    async def structured(self, messages: list[Msg], schema: type[BaseModel], **kw) -> BaseModel: ...
    async def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]: ...
    async def vision(self, prompt: str, images_b64: list[str], **kw) -> str: ...
```

### 6.3 Sovereignty status (M6 → M1)

```json
{"airgap_mode": true, "network_mode": "internal", "dns_resolvable": false,
 "attempts": 4127, "blocked": 4127, "reached": 0, "bytes_egressed": 0,
 "uptime_s": 20635, "last_probe_at": "2026-09-04T10:12:31Z",
 "models": [{"role":"text","name":"llama3.1:8b-instruct-q4_K_M","digest":"sha256:8f1a…","source":"local"},
            {"role":"vision","name":"llava:7b-v1.6-q4_0","digest":"sha256:c3d0…","source":"local"},
            {"role":"embed","name":"bge-m3","digest":"sha256:71ee…","source":"local"}],
 "breach": null}
```

### 6.4 Worker job payload (M3 → M4)

```json
{"job":"ingest","document_id":"uuid","correlation_id":"01J…","attempt":1}
```

Progress is published to Redis channel `ingest:{document_id}`, which M3's SSE endpoint fans out
to the browser as `ingest_progress` frames.

---

## 7. Security Invariants Baked Into These Contracts

```
C1  The client never scopes retrieval. clearance_level, department, filter, and any
    "search these documents" field in a request body are IGNORED by the server.
    Retrieval scope comes only from the verified JWT.
C2  clearance_level and department appear in the Qdrant payload precisely so that the ACL
    can be applied as a PRE-filter. Removing them from the payload breaks the security model.
C3  chunk_refs.id == the Qdrant point id. This lets acl_reverify() join vectors to live
    Postgres labels in one query. Do not generate them independently.
C4  Every SSE `sources` and `citations` frame contains only ACL-approved chunks. The frontend
    is not a filter and must never be relied on as one.
C5  audit_log has no UPDATE or DELETE path. Anything that "needs" to edit an audit row is a
    design error — append a corrective event instead.
C6  documents.clearance_level defaults to the uploader's clearance. A client-supplied
    clearance_level on upload is honoured only for ADMIN, and is audited.
```

---

## 8. Contract Change Request (CCR) Process

```
1  Open an issue titled "CCR: <what changes>" containing: the current shape, the proposed
   shape, the reason, and every member affected.
2  Post it in the team channel. It needs approval from ALL SIX members — a contract change
   with one silent member is how integration breaks.
3  On approval: bump the version at the top of this file (1.0 → 1.1) and log it in §9.
4  The proposer updates, ON THE SAME DAY: this document, M3's OpenAPI + mock server,
   M5's agent mock, M1's generated types, and any fixture affected.
5  Announce "CCR-n merged, re-pull types" in the channel.

After Day 12 (start of P5), contract changes require the Lead's explicit sign-off. After Day 15
they are frozen absolutely — bugs get worked around in implementation, not in the contract.
```

## 9. Change Log

| Version | Date | Change | CCR |
|---|---|---|---|
| 1.0 | Day 2 | Initial freeze | — |

---

## 10. Mock Server (M3, due end of Day 2 — this is what unblocks everyone)

`make mock` starts a FastAPI stub on `:8001` that serves **every** endpoint in §2 with
realistic fixtures, plus a scripted SSE stream that emits the full frame sequence from §3 with
human-plausible delays:

```
route (0 ms) → step×6 (400–1200 ms apart) → sources → token×180 (25 ms apart)
→ citations → done
```

A second scripted turn (`?scenario=approval`) pauses on `approval_required` so M1 can build and
test the approval card before M5's HITL gate exists. A third (`?scenario=denied`) returns an
`ACCESS_DENIED` answer so the RBAC UI states can be built on Day 3.

**Rule:** M1 and M5 develop against the mock until Phase 2 integration. Nobody's progress
depends on anybody else's implementation being finished — only on this contract being honoured.





