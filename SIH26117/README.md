# AEGIS-WB (SIH26117)

## Sovereign On-Premise Agentic AI Workbench

A fully **air-gapped**, multimodal, agentic AI workbench built for confidential
industrial work. Everything — chat, document analysis, data analysis, vision/OCR,
search and model inference — runs **locally on a single on-premise workstation**.
No data ever leaves the machine.

| | |
|---|---|
| Problem statement | Confidential industrial workflow automation without cloud dependence |
| Stack | FastAPI · Next.js 14 (App Router) · arq (Celery-free jobs) · PostgreSQL 16 · Redis 7 · Qdrant · Ollama |
| Models | `llama3.1:8b-instruct-q4_K_M` (LLM), `llava:7b-v1.6` (vision/OCR), `bge-m3` (embeddings) |
| Modes | Fully offline (air-gapped), optional GPU acceleration |
| License / event | SIH26117 — Smart India Hackathon 2026 |

---

## Table of contents

1. [Why AEGIS?](#why-aegis)
2. [Architecture](#architecture)
3. [What it can do](#what-it-can-do)
4. [Quick start](#quick-start)
5. [Pulling models](#pulling-models)
6. [Configuration](#configuration)
7. [Core workflows](#core-workflows)
8. [Security & sovereignty](#security--sovereignty)
9. [Development](#development)
10. [Testing, linting & benchmarks](#testing-linting--benchmarks)
11. [Troubleshooting](#troubleshooting)
12. [Backups](#backups)
13. [Team](#team)
14. [License](#license)

---

## Why AEGIS?

- **Data never leaves the premises.** All inference and RAG run through local
  Ollama, Qdrant and a local PostgreSQL. The `sentinel` service continuously
  probes for accidental egress and reports a Sovereignty status.
- **One command, one workstation.** The whole stack boots with `docker compose up -d`.
- **Grounded answers.** Chat responses are answered strictly from your documents
  when a source is found; otherwise the assistant degrades to a safe open answer
  (offline ChatGPT-style) instead of hallucinating a citation.
- **Tabular documents get instant intelligence.** Upload a CSV/Excel file and the
  workbench auto-generates charts and a structured analysis report.
- **Hash-chained audit trail.** Every significant action is recorded in a
  tamper-evident audit log that can be verified independently.

---

## Architecture

```
                    ┌─────────────────────────── web (Container) ───────────────────────────┐
  Browser (3000) ──▶│  nginx :3000  ── /api/* ──▶ api:8000                                  │
                    │      │                                                                 │
                    │      └── next.js :3001 (frontend app)                                 │
                    └───────────────┬────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────────────┐
              │                     │                             │
              ▼                     ▼                             ▼
      ┌──────────────┐      ┌──────────────┐            ┌──────────────────┐
      │    api       │      │   worker     │            │   sentinel       │
      │  FastAPI     │◀────▶│  arq worker  │            │  egress probe    │
      │  :8000       │      │  (ingest,    │            │  :8001           │
      │              │      │   analysis,  │            │                  │
      └──┬──────┬────┘      │   deliverables)│           └──────┬───────────┘
         │      │           └──┬─────┬───────┘                  │
    appnet   datanet      datanet   modelnet                modelnet
         │      │            │        │                        │
         │      ├───── postgres:5432 │                        │
         │      ├───── redis:6379    │                        │
         │      └───── qdrant:6333   Ø────────────────────────┘
         │                        └───── ollama:11434 (GPU-optional)
```

### Simple Docker and security view

The following diagram shows the Docker services without the internal technical
details. Users enter through the web application. The API controls access to the
data and local AI. The Sentinel watches for unwanted internet access.

```mermaid
flowchart LR
    USER[User] --> WEB[Web app<br/>web :3000]

    subgraph DOCKER[AEGIS-WB Docker workstation]
        subgraph APP[Application network]
            WEB --> API[API<br/>api :8000]
            API --> WORKER[Background worker]
            API --> SENTINEL[Security monitor<br/>sentinel :8001]
        end

        subgraph DATA[Private data network]
            API --> DB[(PostgreSQL<br/>users and audit log)]
            API --> QUEUE[(Redis<br/>job queue)]
            API --> SEARCH[(Qdrant<br/>private search index)]
            WORKER --> QUEUE
            WORKER --> SEARCH
        end

        subgraph MODEL[Private AI network]
            API --> AI[Ollama<br/>local AI models]
            WORKER --> AI
        end

        API --> VAULT[(Encrypted file vault)]
        WORKER --> VAULT
    end

    SENTINEL -. Monitors attempted exit .-> INTERNET((Internet))
    AI -. Document data stays local .-> INTERNET

    classDef public fill:#e8f1ff,stroke:#2563eb,color:#111827
    classDef service fill:#ecfdf5,stroke:#059669,color:#111827
    classDef storage fill:#fff7ed,stroke:#ea580c,color:#111827
    classDef security fill:#fef2f2,stroke:#dc2626,color:#111827
    class USER,WEB public
    class API,WORKER,AI service
    class DB,QUEUE,SEARCH,VAULT storage
    class SENTINEL,INTERNET security
```

**In simple words:** Docker keeps the services organised on the same private
workstation. Only the web app is used by the person. Files are encrypted, the API
checks permissions, the AI runs locally, and important actions are recorded. The
internet is monitored rather than used for document processing.

Three overlay networks isolate concerns:

- **appnet** — API ↔ web ↔ sentinel (application traffic)
- **datanet** — persistent stores: postgres, redis, qdrant
- **modelnet** — Ollama inference only (never exposed to the browser path)

Persistent Docker volumes:

| Volume | Contents |
|---|---|
| `vault` | Encrypted document store, JWT keypair, DB encryption keys |
| `pg_data` | PostgreSQL data |
| `qdrant_data` | Vector index |
| `redis_data` | Queue/job state |
| `ollama_models` | Model weights (loaded once, reused) |

---

## What it can do

| Capability | Description |
|---|---|
| **Grounded chat (RAG)** | Ask questions in natural language; answers cite the source documents via streaming SSE |
| **Open answers** | When nothing relevant is found, falls back to safe general knowledge (offline ChatGPT-style) |
| **Document upload & ingest** | PDF / DOCX / TXT / CSV / XLSX → parsed, OCR'd, chunked (512 tokens), embedded (`bge-m3`, 1024-dim) |
| **Auto-analysis** | Runnable analysis pipeline producing a structured multi-section report (usually < 1 min on realistic files) |
| **Data analysis & charts** | Tabular docs (CSV/Excel) are detected automatically and surface an **Insights** tab with charts |
| **Vision / OCR** | Upload images or image-bearing PDFs; `llava` extracts text and answer visual questions |
| **Instant layouts** | Ask for a layout and get markdown/structured output directly in chat |
| **Deliverables with approval** | Generated outputs require an authorised role to release (HITL approval) |
| **Privileged export** | Admin/authorised flows can export results with clearance checks |
| **Audit trail** | Every chat turn, ingest, login, export and approval appended to a hash-chained ledger |
| **Sovereignty monitoring** | Live egress-airgap status (`:8001/sentinel/status`) |

> No subscription, trial or license gate exists anywhere in the application —
> it is a pure on-premise product.

---

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env — keys MUST match backend/core/config.py exactly (extra keys are rejected)

# 2. Pull models (one-time; requires internet on the build machine)
make pull-models        # or the three `ollama pull` commands below

# 3. Build images (backend, worker, frontend + sentinel)
docker compose build api worker web sentinel

# 4. Start the stack (migrations auto-run at API startup)
docker compose up -d

# 5. Open
#   Frontend            http://localhost:3000
#   API docs (Swagger)  http://localhost:8000/docs
#   Sovereignty status  http://localhost:8001/sentinel/status
```

### Seeded demo account

| Username | Password | Role | Clearance |
|---|---|---|---|
| `green3511` | `Aegis@2026` | ENGINEER | 2 (department ADMIN) |

Login, upload a document, and chat with it — follow the [core workflows](#core-workflows)
below for the happy path.

---

## Pulling models

```bash
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M   # LLM (required)
docker compose exec ollama ollama pull bge-m3                        # embeddings (required)
docker compose exec ollama ollama pull llava:7b-v1.6                 # vision / OCR (optional)
```

- On first chat the API **warms up** the models in a background task so the first
  user turn is fast.
- The Ollama server keeps models resident (`OLLAMA_KEEP_ALIVE` on the daemon) and
  loads **one model at a time** (`OLLAMA_MAX_LOADED_MODELS=1`).
- GPU: `docker-compose.yml` already requests NVIDIA devices; on CPU-only machines
  remove the `deploy.resources` block (or use the provided variants).

### Compose variants

| File | Purpose |
|---|---|
| `docker-compose.yml` | Default stack (GPU reservations if present) |
| `docker-compose.gpu.yml` | Overrides tuned for a GPU workstation |
| `docker-compose.airgap.yml` | Adds air-gap hardening for demo mode (`make demo`) |

---

## Configuration

All settings live in `.env` and are validated by `backend/core/config.py`
(unknown keys are rejected at startup).

| Group | Key | Default / example | Notes |
|---|---|---|---|
| Database | `DATABASE_URL` | `postgresql+asyncpg://aegis:...@postgres:5432/aegis_wb` | asyncpg URL |
| Vectors | `QDRANT_URL` | `http://qdrant:6333` | — |
| Vectors | `QDRANT_COLLECTION` | `aegis_bge_m3_1024` | must match `EMBED_DIM` |
| Queue | `REDIS_URL` | `redis://redis:6379/0` | arq worker queue |
| Sentinel | `SENTINEL_URL` | `http://sentinel:8001` | egress probe |
| Ollama | `OLLAMA_URL` | `http://ollama:11434` | — |
| Ollama | `LLM_MODEL` | `llama3.1:8b-instruct-q4_K_M` | chat/analysis engine |
| Ollama | `VISION_MODEL` | `llava:7b-v1.6` | OCR + image Q&A |
| Ollama | `EMBED_MODEL` / `EMBED_DIM` | `bge-m3` / `1024` | ingest embeddings |
| Ollama | `OLLAMA_TIMEOUT_S` | `60` | per-call timeout |
| Ollama | `OLLAMA_KEEP_ALIVE` | `30m` | per-request keep-alive (use `30m`, **not** `-1` — daemons reject `-1` per-request) |
| Auth | `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | `/data/keys/jwt_*.pem` | RSA keypair in `vault` |
| Auth | `ACCESS_TOKEN_TTL_MIN` / `REFRESH_TOKEN_TTL_H` | `15` / `8` | — |
| Upload | `MAX_UPLOAD_MB` / `VAULT_PATH` | `200` / `/data/vault` | encrypted at rest |
| RAG | `CHUNK_TARGET_TOKENS` | `512` | chunk size |
| RAG | `RETRIEVAL_TOP_K` / `RERANK_TOP_K` | `20` / `5` | retrieve then rerank |
| RAG | `ENABLE_RERANKER` / `ENABLE_OCR` / `ENABLE_VISION` | `true` | feature switches |
| Agent | `MAX_AGENT_ITERATIONS` / `TURN_DEADLINE_S` | `3` / `60` | planner loop caps |
| App | `APP_ENV` / `LOG_LEVEL` | `development` / `INFO` | set `AIRGAP_MODE=true` for hardened behaviour |

`AIRGAP_MODE=true` (or the airgap compose file) disables any background network
access path and reports full sovereignty status.

---

## Core workflows

### 1. Upload + ingest a document

1. **Documents** tab → upload (PDF/DOCX/TXT/CSV/XLSX/image, up to `MAX_UPLOAD_MB`).
2. Status flows `QUEUED → PROCESSING → READY` (worker job).
3. On READY the file is chunked (512 tokens), rerank-scored vectors indexed, and
   stored encrypted in the `vault`.
4. Uploaded files appear in the **Documents** table. Click a tabular file to
   auto-open the **Insights** tab.

### 2. Chat with grounded answers

1. **Chat** → new chat (auto-titled from your first message).
2. Type a question. The assistant streams tokens, **sources** and **citations**
   live over SSE.
3. Answers try to cite the uploaded documents; if nothing relevant is retrieved,
   the model answers freely (general knowledge) and marks the turn accordingly.

### 3. Tabular auto-analysis

Upload a CSV/Excel → the workbench auto-switches to the **Insights** tab and:
- generates charts built from the file itself,
- produces a structured multi-section analysis report (overview, key metrics,
  segment breakdown, issues/risks, recommendations),
- streams progress with a clear on-screen status (`Running the local AI…`).

### 4. Deliverables & approvals

Analysis results can be promoted to a **deliverable** and require an authorised
actor to approve before they are considered released. Every step is audited.

---

## Security & sovereignty

- **Encryption at rest** — documents are encrypted (AEAD) with keys held in the
  `vault`; local RSA keypair signs/verifies JWTs.
- **RBAC + clearance** — roles (`ENGINEER`, `AUDITOR`, `ADMIN`, …) and clearance
  levels gate document access, cross-department reads, privileged export and
  role minting. Non-admins can never mint privileged roles.
- **Hash-chained audit** — audit entries chain hashes; `POST /audit/verify`
  re-verifies the whole trail and exposes `SovereigntyStatus`.
- **Air-gap monitoring** — the `sentinel` service probes for unintended egress
  and reports live status at `:8001`; the API refuses disconnected dependencies.
- **Egress is opt-out by default** — only the model-pull step needs internet,
  on the build machine; runtime is designed to run zero-egress.

---

## Development

```bash
make up         # build + start everything
make up-dev     # explicit service list
make logs       # follow all logs
make down       # stop
make mock       # local-only API server for frontend work
make types      # regenerate TS types from the OpenAPI schema
make seed       # run data normalisation + migrate to head
make migrate    # autogenerate + apply an alembic migration
make smoke      # health-check every service (API, web, Qdrant, Ollama)
make bench      # latency benchmark (profile B)
make demo       # air-gapped demo compose
make check-loc  # LOC gate report
```

### Frontend-only dev

```bash
cd frontend && npm install && npm run dev
```

The frontend talks to the same `/api`-prefixed routes through nginx in the
compose stack; set `NEXT_PUBLIC_API_URL` if you point it elsewhere.

---

## Testing, linting & benchmarks

```bash
make test        # pytest backend/tests (111 passing)
docker compose exec -T -e PYTHONPATH=/app api python -m pytest backend/tests -q

make lint        # ruff + mypy (backend) + tsc --noEmit (frontend)

make bench       # bench/latency.py
ls bench/        # per-profile latency & throughput scripts
```

CI-style gate: types + lint + typecheck run as part of `next build`; the API
startup also fails fast on misconfigured `.env`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Browser shows an old broken page after a fix | Hard refresh (**Ctrl+F5**) — Next bundles are cached client-side |
| `keep_alive: "-1"` → 400 Bad request from Ollama | Set `OLLAMA_KEEP_ALIVE=30m` in `.env`; `-1` is only valid as a daemon env var |
| First message sends but no output appears | You are running a stale bundle — rebuild web and hard-refresh (this was fixed in the new-chat navigation race) |
| Sidebar sessions missing | Rebuilt frontend reads the paginated `{items, …}` envelope — rebuild web |
| Chat name stays "New Chat" | Rebuilt API auto-titles sessions on the first message; restart the `api` container |
| Slow first chat turn | Normal — the API warms up models in the background on startup; subsequent turns are fast |
| `rg` not found / PowerShell quirk | Use `Select-String -Pattern …` on Windows; probes must run inside `sih26117-api-1` (web has no Python) |
| Permissions error deleting `/tmp/probe_*` as default user | `docker compose exec -T -u root api sh -c 'rm -f /tmp/probe_*'` |

---

## Backups

```bash
make backup            # pg_dump to a timestamped SQL file
make restore file=backup_20260908_1200.sql   # restore from dump
# File contents live in the `vault` volume (encrypted) — back that up too.
```

---

## Team

| Member | Focus | Owned paths |
|---|---|---|
| M1 | Frontend / UI | `frontend/` |
| M2 | Data engineer | `data_pipeline/` |
| M3 | Backend & security | `backend/{api,core,db,schemas,services/{crypto,audit}}` |
| M4 | AI & RAG | `backend/{services/{ingest,rag},worker}` |
| M5 | Agentic workflow | `backend/agents/` |
| M6 | Integration lead | `docker-compose*`, `Makefile`, `tools/` |

---

## License

SIH26117 — Smart India Hackathon 2026.