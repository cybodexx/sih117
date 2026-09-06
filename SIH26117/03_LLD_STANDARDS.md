# SIH26117 — Low-Level Design Constraints & Coding Standards
### Binding on all six members · v1.0

> These are not style suggestions. They are the reason six people using AI coding agents in
> parallel will produce one coherent system instead of six incompatible ones. CI enforces the
> mechanical rules; review enforces the rest.

---

## 1. The Three Laws

```
LAW 1 — STRICT MODULARITY
        One file, one responsibility. If you cannot describe a file's job in a single
        sentence without the word "and", split it.

LAW 2 — 300 LINES MAXIMUM
        No source file exceeds 300 physical lines, including imports, excluding tests.
        This is a hard CI gate, not a guideline.

LAW 3 — ABSOLUTE SIMPLICITY
        Write the most boring code that solves today's requirement. No speculative
        abstraction, no plugin systems, no config for things that never vary,
        no design pattern you cannot justify in one sentence.
```

**Why Law 2 in an AI-assisted project specifically:** a 300-line ceiling keeps every file small
enough to fit entirely in a coding agent's working context. The agent can then reason about the
whole file instead of guessing at the parts it cannot see — which is where hallucinated APIs and
silent regressions come from. Small files are also mergeable; 1 200-line files are where six-way
merges go to die.

---

## 2. Mechanical Limits (enforced by CI)

| Limit | Value | Applies to | Tool |
|---|---|---|---|
| Lines per file | **300** hard | all `.py`, `.ts`, `.tsx` | `tools/check_loc.py` |
| Lines per React component file | **200** target / 300 hard | `.tsx` | `check_loc.py --warn 200` |
| Lines per function | **50** | all | `ruff PLR0915`, `eslint max-lines-per-function` |
| Function parameters | **4** (then use a Pydantic model / props object) | all | `ruff PLR0913` |
| Cyclomatic complexity | **10** | all | `ruff C901`, `eslint complexity` |
| Nesting depth | **4** | all | review |
| Line length | **100** | all | `black`, `prettier` |
| Import depth | no `from ..` beyond one level up | Python | review |
| `any` / `Any` | **0** in new code (documented exceptions only) | TS / Python | `tsc --strict`, `mypy` |

### 2.1 The LOC gate (owner M6 — commit this on Day 1)

```python
# tools/check_loc.py — run by pre-commit and CI. Deliberately tiny and dependency-free.
"""Fail the build if any source file exceeds the LOC ceiling."""
import sys, pathlib

HARD, WARN = 300, 200
ROOTS = ["backend", "frontend", "data_pipeline", "eval", "tools"]
EXTS = {".py", ".ts", ".tsx"}
SKIP = {"node_modules", ".next", "__pycache__", "alembic/versions", ".venv", "dist", "types.gen.ts"}

def offenders() -> list[tuple[str, int]]:
    bad = []
    for root in ROOTS:
        for p in pathlib.Path(root).rglob("*"):
            if p.suffix not in EXTS or any(s in p.as_posix() for s in SKIP):
                continue
            if "/tests/" in p.as_posix():          # tests may be longer than the code
                continue
            n = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
            if n > HARD:
                bad.append((p.as_posix(), n))
            elif n > WARN and p.suffix == ".tsx":
                print(f"::warning:: {p} is {n} lines (target {WARN})")
    return bad

if __name__ == "__main__":
    bad = offenders()
    for path, n in bad:
        print(f"LOC VIOLATION  {path}: {n} lines (max {HARD}) — split this file")
    sys.exit(1 if bad else 0)
```

### 2.2 How to split a file that is growing past 300 lines

| Symptom | Split into |
|---|---|
| A router with route bodies containing logic | `api/v1/x.py` (routes) + `services/x_service.py` (logic) |
| A service doing fetch **and** transform **and** persist | `x_fetch.py`, `x_transform.py`, `x_repo.py` |
| A parser handling three formats | `pdf_parser.py`, `image_parser.py`, `tabular_parser.py` + a `router.py` dispatch table |
| A React component with 5 `useState` and inline handlers | presentational `X.tsx` + `useX.ts` hook + `X.types.ts` |
| A god-object model file | one file per SQLAlchemy model under `db/models/` |
| A prompt file over 300 lines | `prompts/{router,synth,vision,compliance}.py` |
| A long `if/elif` chain | a module-level dispatch `dict[Enum, Callable]` |

---

## 3. Architectural Rules

### 3.1 Layering (dependencies point downward only)

```
api/         → may import: schemas, core, services, agents            (NEVER db.models directly)
agents/      → may import: schemas, core, services                    (NEVER api)
services/    → may import: schemas, core, db.repositories             (NEVER api, NEVER agents)
db/          → may import: core                                       (NEVER services, api, agents)
core/        → imports nothing from the project except schemas
schemas/     → imports nothing from the project
```

A cyclic import is a design error, not a problem to solve with a late import inside a function.
`tools/check_layers.py` (optional, 30 lines) can assert this with a grep.

### 3.2 Thin controllers — the single most-violated rule

```python
# ✅ CORRECT — api/v1/chat.py stays under 100 LOC forever
@router.post("/{session_id}/messages", response_model=MessageAccepted, status_code=202)
async def post_message(
    session_id: UUID,
    body: MessageCreate,
    user: ServerUserContext = Depends(get_current_user),
    svc: ChatService = Depends(get_chat_service),
) -> MessageAccepted:
    """Accept a user turn and start the agent run. Validation + delegation only."""
    return await svc.submit(session_id, body, user)
```

```python
# ❌ WRONG — logic in the route. This file will be 800 lines by Phase 4.
@router.post("/{session_id}/messages")
async def post_message(session_id, body, db=Depends(get_db)):
    session = await db.get(ChatSession, session_id)      # data access in a route
    if not session: raise HTTPException(404)
    chunks = await qdrant.search(...)                     # retrieval in a route
    prompt = f"..."                                       # prompt building in a route
    ...
```

### 3.3 Dependency injection, always

Every external resource arrives through `Depends()` (Python) or props/context (React). No module
constructs its own DB session, HTTP client, Qdrant client, or LLM client at import time.

```python
# core/deps.py — the only place clients are constructed
async def get_db() -> AsyncIterator[AsyncSession]: ...
async def get_qdrant() -> AsyncQdrantClient: ...
async def get_llm() -> OllamaClient: ...
async def get_current_user(token=Depends(oauth2), db=Depends(get_db)) -> ServerUserContext: ...
def require_role(*roles: Role) -> Callable: ...
def require_clearance(level: Clearance) -> Callable: ...
```

This is what makes tests possible without Docker: override the dependency, inject a fake.

### 3.4 Typed boundaries

Every value crossing a process, network, or module boundary is a Pydantic model (Python) or an
interface generated from OpenAPI (TypeScript). Raw `dict` in a function signature is banned
outside `payload`-shaped Qdrant/JSON plumbing.

### 3.5 Error handling

```python
# core/exceptions.py — one hierarchy, one handler, one response shape
class AegisError(Exception):
    code: str; status: int; detail: str          # subclasses set these

class NotFound(AegisError):        code="not_found";        status=404
class Forbidden(AegisError):       code="forbidden";        status=403
class ClearanceDenied(Forbidden):  code="clearance_denied"
class IngestError(AegisError):     code="ingest_failed";    status=422
class ModelUnavailable(AegisError):code="model_unavailable";status=503
class BudgetExceeded(AegisError):  code="budget_exceeded";  status=429
```

One `@app.exception_handler(AegisError)` maps everything to RFC 9457 `problem+json`:

```json
{"type":"/errors/clearance_denied","title":"Insufficient clearance","status":403,
 "detail":"This document requires RESTRICTED clearance.","correlation_id":"01J…"}
```

Banned: bare `except:`, `except Exception: pass`, returning `None` to signal failure, and
raising `HTTPException` from anywhere except an `api/` module.

### 3.6 Configuration

```python
# core/config.py — the ONLY place os.environ is read. Everything else imports `settings`.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="forbid")
    postgres_dsn: PostgresDsn
    qdrant_url: AnyHttpUrl
    ollama_url: AnyHttpUrl
    llm_model: str = "llama3.1:8b-instruct-q4_K_M"
    vision_model: str = "llava:7b-v1.6"
    embed_model: str = "bge-m3"
    embed_dim: int = 1024
    jwt_private_key_path: Path
    access_token_ttl_min: int = 15
    max_upload_mb: int = 200
    chunk_target_tokens: int = 512
    retrieval_top_k: int = 20
    rerank_top_k: int = 5
    max_agent_iterations: int = 3
    turn_deadline_s: int = 60
    enable_reranker: bool = True          # off on Profile C hardware
    enable_ocr: bool = True
    enable_vision: bool = True
    airgap_mode: bool = True

settings = Settings()   # import this; never call os.getenv anywhere else
```

`extra="forbid"` means a typo'd env var fails at boot instead of silently defaulting at 02:00 on
demo night.

### 3.7 Naming

| Thing | Convention | Example |
|---|---|---|
| Python module | `snake_case`, noun | `hash_chain.py` |
| Python class | `PascalCase` | `ServerUserContext` |
| Python function | `snake_case`, verb-first | `build_acl_filter()` |
| Async function | no `async_` prefix — the signature says it | `async def embed_batched()` |
| Boolean | `is_` / `has_` / `can_` / `enable_` | `can_read`, `enable_reranker` |
| Pydantic request/response | `XCreate` / `XUpdate` / `XRead` / `XAccepted` | `MessageCreate` |
| React component file | `PascalCase.tsx` | `CitationChip.tsx` |
| React hook | `useX.ts` | `useChatStream.ts` |
| Zustand store | `xStore.ts` | `chatStore.ts` |
| Test | `test_<unit>__<behaviour>` | `test_can_read__denies_cross_department` |
| Qdrant collection | `aegis_<model>_<dim>` | `aegis_bge_m3_1024` |
| SSE event | `snake_case` | `approval_required` |

### 3.8 Async discipline

- Every I/O function is `async`. Mixing sync DB calls into the event loop stalls streaming.
- CPU-bound or blocking libraries (`bcrypt`, `libmagic`, `PyMuPDF`, `PaddleOCR`,
  `CrossEncoder`) run via `run_in_threadpool` / the ARQ worker — never inline in a request.
- Every outbound call has an explicit timeout. No unbounded `await`.
- Fan-out uses `asyncio.gather` with `return_exceptions=True`, and you handle the exceptions.
- One `AsyncSession` per request. Never share a session across tasks.

---

## 4. Security Coding Rules (non-negotiable)

```
S1  Never trust the client. Filters, clearances, department, document ids, and prices of any
    kind are derived server-side from the verified JWT.
S2  Every Qdrant search passes a filter built by build_acl_filter(). Calling
    qdrant.search() outside services/rag/ is a review-blocking violation.
S3  Parameterised SQL only. No f-string SQL, ever, including in the NL→SQL tool.
S4  No secret, token, password, DEK, or document body in any log line. structlog runs a
    redaction processor; do not bypass it with print().
S5  Fail closed. Unknown clearance, unparseable label, unreachable dependency → deny.
S6  New documents inherit the uploader's clearance, never PUBLIC.
S7  Retrieved document text is wrapped in <untrusted_data> and can never trigger a tool call.
S8  Every state-changing or data-reading action emits exactly one audit event.
S9  No network egress from app/data/model tiers. Adding a dependency that phones home
    (telemetry, font CDN, model auto-download) fails the air-gap CI test.
S10 Model output is never exec()'d, eval()'d, or shelled out. Parse, validate, then act.
```

---

## 5. AI-Assisted Development Protocol ("vibe-coding" rules)

Every member drives a coding agent (Antigravity, OpenCode, Claude Code, …). These rules exist so
six agents working in parallel converge instead of diverging. **They also directly control token
spend, which matters on a fixed budget.**

### 5.1 The context contract

Before generating code, paste into your agent — **in this order**:

```
1. Your member brief          (member_briefs/MEMBER_n_*.md)   ← your scope, nothing else
2. 04_INTEGRATION_CONTRACTS.md §(only the sections you touch)  ← the frozen interfaces
3. This file, §1–§3                                            ← the standards
4. The exact file you are editing, or the exact file path to create
```

Do **not** paste the whole documentation set into every prompt. Paste the relevant sections. A
5 000-token prompt that produces correct code is cheaper than three 2 000-token prompts that
produce code you throw away.

### 5.2 Hard rules for prompting

| Rule | Why |
|---|---|
| **Always state the LOC ceiling in the prompt.** "≤ 250 lines; split into multiple files if larger." | Agents default to monoliths |
| **Name the exact file path** you want created or edited | Prevents inventing a parallel structure |
| **Paste the real contract**, never a paraphrase | The #1 cause of integration failure is a hallucinated field name |
| **Forbid touching files you do not own** | "Do not modify anything outside `backend/agents/`." |
| **Ask for one file per request** | Multi-file generations are where agents drift and truncate |
| **Demand type annotations and docstrings** | Cheap to ask for, expensive to add later |
| **Require the test in the same request** | "Also write `tests/unit/test_chunker.py` covering the atomic-table case." |
| **Pin versions in the prompt** | Otherwise you get a `langchain 0.0.x` API that no longer exists |
| **Never accept code you cannot explain** | You will be asked to explain it by a judge, live |

### 5.3 The prompt skeleton every member reuses

```
ROLE:     You are a senior <domain> engineer on an air-gapped industrial AI project.
CONTEXT:  <paste the relevant contract section verbatim>
STACK:    <pinned versions from 00_MASTER_SRS.md §5>
TASK:     Create exactly one file: <path>. It must <one-sentence responsibility>.
CONSTRAINTS:
  - ≤ 250 lines. If it would exceed that, tell me how to split it and generate the first file.
  - Full type annotations. Async for all I/O. Explicit timeouts.
  - Import settings from core.config; never call os.getenv.
  - Raise AegisError subclasses; never HTTPException outside api/.
  - No new dependencies beyond the pinned list. No network calls to anything but
    localhost services — this system is air-gapped.
  - Do not modify or reference files outside <your directory>.
OUTPUT:   The complete file, then a 3-line summary of what I must wire up next.
```

### 5.4 Token budget discipline (shared ~$90 across the team)

| Practice | Saving |
|---|---|
| One file per prompt, with the contract pasted | Avoids the throwaway-regeneration loop, the single biggest waste |
| Reuse a long-lived session per module instead of re-pasting context | Prompt caching makes follow-ups far cheaper |
| Use a smaller/faster model for boilerplate (CRUD, DTOs, Tailwind markup) and reserve the strongest model for the chunker, supervisor, RBAC, and compose files | These four are where correctness actually pays |
| Never ask an agent to "review the whole repo" | Enormous input cost, low yield |
| Fix small errors by hand | A 3-line typo fix does not need a model call |
| Keep files ≤ 300 lines | Small files mean small prompts, permanently |
| Write the test first when behaviour is subtle | One prompt instead of five rounds of "still wrong" |

### 5.5 What a coding agent must never be asked to invent

Generate these **once**, by hand or by agreement, then treat them as immutable inputs:
the API contract, the SSE frame schema, the `AgentState` shape, the Qdrant payload schema,
the DB column names, and the model names. If an agent "improves" one of these, you get a
compile-clean system that fails only at integration — the most expensive possible failure mode.

---

## 6. Review Checklist (paste into every PR)

```
FUNCTION
□ Solves the stated requirement, nothing more
□ Manually exercised inside docker compose, not just unit-tested

STRUCTURE
□ ≤ 300 LOC file / ≤ 50 LOC function / ≤ 4 params / complexity ≤ 10
□ One responsibility, describable in one sentence
□ Layering respected; no cyclic imports; no logic in api/
□ No duplicated helper that already exists elsewhere

TYPES & ERRORS
□ Fully annotated; mypy / tsc strict clean; no Any
□ AegisError subclasses; no bare except; no None-as-error

SECURITY
□ Rules S1–S10 satisfied
□ ACL filter present on every retrieval path touched
□ No secrets or document content in logs
□ Audit event emitted for every state change / data read

OPS
□ settings used, no os.getenv
□ Timeouts on every I/O call
□ Structured log with correlation_id at the entry point
□ Works with the reranker/OCR/vision flags OFF (Profile C)

TESTS & DOCS
□ Unit tests added and passing; CI green
□ Module doc page updated
```

---

## 7. Anti-Patterns (auto-reject in review)

| Anti-pattern | Correct approach |
|---|---|
| `utils.py` / `helpers.py` / `misc.py` | Name the actual responsibility: `token_counter.py` |
| `manager.py`, `handler.py`, `processor.py` | Say what it does: `chunk_indexer.py` |
| Business logic in a route handler | Move it to `services/` |
| `except Exception: pass` | Catch the specific error; log it; re-raise or convert |
| Fixed-size character chunking | Layout-aware semantic chunking (`01_ALGORITHMS.md §1.5`) |
| Post-filtering retrieval results by clearance | Pre-filter inside the Qdrant query |
| `os.getenv` sprinkled through the codebase | `core/config.settings` |
| A 900-line `models.py` | One file per model under `db/models/` |
| Hard-coded model name in three places | `settings.llm_model` |
| A React component with 400 lines and 6 `useState` | Extract a hook and sub-components |
| `# TODO: add auth later` | Add it now or delete the endpoint |
| Speculative interface with one implementation | Write the concrete class; abstract when the second arrives |
| `sleep()` in a test | Await the real condition, or use a fake clock |





