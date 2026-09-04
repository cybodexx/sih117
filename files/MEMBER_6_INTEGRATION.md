# MEMBER 6 — Team Lead / Integration Architect
### SIH26117 · Personal Brief · v1.0

**Read with:** `00_MASTER_SRS.md` (full document — you are responsible for all of it),
`01_ALGORITHMS.md §3.1` (your air-gap topology), and `04_INTEGRATION_CONTRACTS.md §6.2, 6.3`
(your LLM client and sovereignty status contracts). You need to read every other brief at
a high level — you are the one who makes them interoperate.

---

## Your mandate

You are the system. M1–M5 each build a module. You make those modules run together as a
single, provably air-gapped workbench that a judge can interrogate for six straight minutes
without a single crash, stall, or outbound byte. Two things are yours alone: **the LLM
runtime that every other module depends on**, and **the Docker network topology that makes
the sovereignty claim not just asserted, but architecturally true**.

**You own:** `docker-compose.yml`, `docker-compose.airgap.yml`, `services/llm/ollama_client.py`,
`aegis-sentinel/`, `Makefile`, `bench/`, and the final demo script.

---

## Phase deliverables

| Phase | Build | Done when |
|---|---|---|
| **P1** | Pull and verify models: `llama3.1:8b-instruct-q4_K_M` (text), `llava:7b-v1.6-q4_0` (vision), `bge-m3` (embed). Write `services/llm/ollama_client.py` — the **single LLM entry point** for the whole codebase (§6.2). Write `bench/latency.py` to measure time-to-first-token. Record model digests in `models.lock`. | `bench/latency.py` prints p95 TTFT ≤ 2.5 s on target hardware; `sha256sum` of every pulled model matches `models.lock` |
| **P2** | `docker-compose.yml` (development): all 7 services (`web`, `api`, `worker`, `ollama`, `qdrant`, `postgres`, `sentinel`) with correct port mappings, volume mounts, env files, and a shared `appnet`. Health-check on every service. `Makefile` targets: `make up`, `make down`, `make logs`, `make mock`, `make types`, `make seed`. | `make up` starts all services with 0 crash-loops; `make mock` serves M3's mock server; every health-check turns green within 60 s |
| **P3** | End-to-end integration wire-up. Confirm M3's API → M5's agents → M4's Qdrant → M6's Ollama round-trip works with a real query. Write `tests/e2e/test_full_turn.py`: POST a message, consume the SSE stream to `done`, assert `grounded=true` and at least one citation. | `pytest tests/e2e/test_full_turn.py` passes green against the live stack; the "Turbine-4 trip" query returns a multi-citation answer |
| **P4** | `docker-compose.airgap.yml`: 4 networks — `edge` (bridge, host-accessible), `appnet`, `datanet`, `modelnet` (all `internal: true`, no gateway). Assign each service to the minimum required networks (§3.1 topology). `aegis-sentinel/` service: polls 4 external targets every 5 s, exposes `GET /sentinel/status` (§6.3 contract). `tests/security/test_no_egress.py` | `pytest tests/security/test_no_egress.py` passes (TCP connect to `1.1.1.1:53` and `huggingface.co:443` fails from `api`, `worker`, `ollama`); sentinel panel shows `reached: 0` |
| **P5** | Performance sweep: HNSW `m`/`ef_construct` vs. recall trade-off, Ollama `num_ctx`, `num_batch`, `keep_alive=-1`, GPU layer count. Write `bench/gpu_monitor.py` (polls `nvidia-smi` every 2 s during a load test, prints VRAM peak and GPU %). Run 10 concurrent queries; assert no OOM, no crash. Document the final model config in `docs/HARDWARE_PROFILES.md` for 3 hardware tiers (A, B, C). | `bench/latency.py` p95 TTFT ≤ 2.5 s at concurrency 3; VRAM stays below 90%; `docs/HARDWARE_PROFILES.md` committed |
| **P6** | The demo. Write `docs/DEMO_SCRIPT.md`: the 6-minute "Incident War Room" storyline beat by beat, including the exact prompts to type, which windows to have open, and the fallback plan if the GPU is slow. Ensure `make seed` populates the demo corpus deterministically. Conduct 3 full dress rehearsals with the team. | The team completes the 6-minute run 3 consecutive times without a crash, a slow response, or an outbound byte detected |

---

## Your seven technical problems

1. **GPU passthrough in Docker.** Nvidia container toolkit must be installed on the host
   *before* Docker is configured. The device IDs must be correct in `deploy.resources.reservations`.
   Verify with `docker run --rm --gpus all nvidia/cuda:12-base nvidia-smi` before doing anything
   else. If this fails, nothing else works and you waste the whole team's Day 1.

2. **Internal networks have no gateway.** `internal: true` Docker bridge networks cannot route
   off-host — which is exactly what we want. But this also means no `apt-get`, no `pip install`,
   no `npm install` inside those containers at runtime. Every dependency must be in the image.
   Build and push all images before switching to airgap mode. Test the full stack offline before
   the demo day, not on demo day.

3. **`keep_alive=-1` is mandatory during the demo.** Ollama unloads a model after 5 minutes of
   inactivity by default. If a judge pauses to ask a question for 6 minutes, the next prompt
   triggers a cold load (8–20 s). Set `OLLAMA_KEEP_ALIVE=-1` in the container env. Verify by
   sending a request after a 10-minute idle and checking that TTFT stays under 3 s.

4. **The `ollama_client.py` is the single LLM bottleneck.** Every module (M4 for embeddings, M5
   for chat and structured output) imports this one file. If you implement it with a synchronous
   `requests` call, the whole FastAPI event loop blocks on every LLM token. It must be
   `async def stream() -> AsyncIterator[str]` using `httpx.AsyncClient`. One blocking call during
   the demo will freeze the SSE stream and M1's typing animation, which looks catastrophic.

5. **Model digest pinning.** You pull models before the event. On demo day, never run
   `ollama pull` — it attempts an internet connection and will fail on the airgap network. Store
   model weights in the `ollama_models` named volume. Record `sha256` digests in `models.lock`.
   Any model that has not been pre-pulled is a demo blocker.

6. **Service startup order.** PostgreSQL and Qdrant must be `healthy` before the API starts.
   The API must be `healthy` before the worker starts. Ollama must finish loading the model
   into VRAM before the first embedding request hits it. Use `depends_on: condition:
   service_healthy` in `docker-compose.yml` and write proper health-check commands for each
   service — not just `test: ["CMD", "true"]`.

7. **The pitch is technical theatre.** Judges have seen chatbots. They are looking for proof,
   not claims. Every slide must have a corresponding live demo beat. The sovereignty panel must
   be *visible* on screen at all times during the demo — not a separate tab. Plan the 1080p
   projector layout in `docs/DEMO_SCRIPT.md` (e.g., a split view with the chat on the left and
   the proof panel on the right). Rehearse on the *same* hardware, same resolution.

---

## Ready-to-paste AI prompts

Paste the referenced contract section **verbatim** with each prompt. One file per request.

### P1 — Ollama client (the entire codebase depends on this)

```
You are a senior DevOps and AI architect. Stack: Python 3.11, httpx 0.27 (async),
Pydantic 2.7, asyncio. This system is AIR-GAPPED: Ollama runs at http://ollama:11434
inside Docker. No LangSmith, no OpenAI fallback, no external API of any kind.

Create exactly one file: backend/services/llm/ollama_client.py  (≤ 200 lines)

This is the ONLY file in the codebase that talks to Ollama. Every other module imports it.

EXACT PUBLIC INTERFACE (contractual — do not rename, do not add parameters):
<paste 04_INTEGRATION_CONTRACTS.md §6.2 verbatim>

REQUIREMENTS
- All methods are async. Use httpx.AsyncClient with connection pooling (limits=10).
- stream() yields str deltas as they arrive from Ollama's /api/chat stream. It must NOT
  buffer the whole response — yield each delta the moment it arrives.
- structured() calls chat() and parses the response as the given Pydantic schema.
  Use Ollama's format=json mode. On parse failure: retry once, then raise OllamaError.
- embed() calls /api/embeddings in batches of 32. Asserts len(result[0]) == 1024 to
  guard against a silent model swap.
- vision() calls /api/generate with images (base64-encoded). Uses the vision model,
  not the text model — read both from settings.ollama_vision_model.
- All methods: asyncio.timeout(settings.ollama_timeout_s), structured logging on error,
  exponential retry 3× on connection errors only — not on model errors.
- LANGCHAIN_TRACING_V2=false: never import langsmith or call any tracing endpoint.
- No secret or prompt body may appear in any log line.

CONSTRAINTS — ≤ 200 lines, fully typed, no `any`.
Output the complete file, then 3 lines on what to wire next.
```

### P2 — docker-compose.yml (development stack)

```
Act as a Principal DevOps Architect. You are writing the development docker-compose.yml
for an on-premise AI workbench. All images are pre-built and available locally.

Create exactly one file: docker-compose.yml  (≤ 200 lines)

Services and their constraints:

web:
  image: aegis-web:latest
  ports: ["3000:3000"]
  env_file: .env.web
  depends_on: api (service_healthy)
  networks: [appnet]

api:
  image: aegis-api:latest
  ports: ["8000:8000"]
  env_file: .env.api
  depends_on: postgres (service_healthy), qdrant (service_healthy), ollama (service_healthy)
  networks: [appnet, datanet, modelnet]
  healthcheck: GET http://localhost:8000/health every 10s, 3 retries, start_period 20s

worker:
  image: aegis-worker:latest
  env_file: .env.api         # same env as api
  depends_on: api (service_healthy), redis (service_healthy)
  networks: [appnet, datanet, modelnet]

ollama:
  image: ollama/ollama:latest
  volumes: [ollama_models:/root/.ollama]
  deploy.resources.reservations.devices: [{driver: nvidia, count: all, capabilities: [gpu]}]
  environment: OLLAMA_KEEP_ALIVE=-1, OLLAMA_HOST=0.0.0.0
  networks: [modelnet]
  healthcheck: GET http://localhost:11434/api/tags every 15s, start_period 30s

qdrant:
  image: qdrant/qdrant:v1.9.7
  volumes: [qdrant_data:/qdrant/storage]
  environment: QDRANT__TELEMETRY_DISABLED=true
  networks: [datanet]
  healthcheck: GET http://localhost:6333/readyz every 10s

postgres:
  image: postgres:16-alpine
  volumes: [pg_data:/var/lib/postgresql/data]
  env_file: .env.postgres
  networks: [datanet]
  healthcheck: pg_isready -U aegis every 5s

redis:
  image: redis:7-alpine
  networks: [datanet]
  healthcheck: redis-cli ping every 5s

sentinel:
  image: aegis-sentinel:latest
  networks: [appnet, datanet, modelnet]

Named volumes: ollama_models, qdrant_data, pg_data, redis_data
Network: appnet (bridge, not internal — development only)

CONSTRAINTS — ≤ 200 lines, no hardcoded secrets (use env_file), no `latest` for
qdrant or postgres (pin to the versions above). Add a comment above every service
explaining what it does in one line. Output the file + 3 lines on what to wire next.
```

### P4 — Air-gapped network topology

```
Principal DevOps Architect. Docker Compose v2, Linux. AIR-GAPPED production deployment.

Create exactly one file: docker-compose.airgap.yml  (≤ 150 lines)

This overrides docker-compose.yml for production. The key difference: ALL inter-service
networks are internal: true (no default gateway → no route off-host). Only the `edge`
network is external-facing and ONLY the `web` service touches it.

EXACT NETWORK TOPOLOGY (from 01_ALGORITHMS.md §3.1 — implement verbatim):
  edge:     driver: bridge                    # host can reach web:3000 only
  appnet:   driver: bridge, internal: true    # no gateway, no egress
  datanet:  driver: bridge, internal: true
  modelnet: driver: bridge, internal: true

SERVICE → NETWORK ASSIGNMENTS:
  web:      edge, appnet
  api:      appnet, datanet, modelnet         # NOT on edge
  worker:   appnet, datanet, modelnet
  ollama:   modelnet                          # fully sealed
  qdrant:   datanet
  postgres: datanet
  redis:    datanet
  sentinel: appnet, datanet, modelnet

ADDITIONAL AIR-GAP SETTINGS (add to every service's environment):
  HF_HUB_OFFLINE=1
  TRANSFORMERS_OFFLINE=1
  HF_DATASETS_OFFLINE=1
  ANONYMIZED_TELEMETRY=false
  QDRANT__TELEMETRY_DISABLED=true
  DO_NOT_TRACK=1
  NEXT_TELEMETRY_DISABLED=1
  LANGCHAIN_TRACING_V2=false
  no_proxy=*
  HTTP_PROXY=""
  HTTPS_PROXY=""

Internal services: dns: ["127.0.0.1"]   # external hostnames cannot resolve

CONSTRAINTS — ≤ 150 lines. Output the file + 3 lines on what to verify next.
```

### P4 — Egress Sentinel service

```
Senior Python engineer. Stack: Python 3.11, FastAPI 0.111, asyncio. AIR-GAPPED.

Create exactly one file: aegis-sentinel/main.py  (≤ 150 lines)

A lightweight FastAPI service that continuously proves data sovereignty.

BACKGROUND TASK (runs on startup, loops every 5 s):
  targets = [
    ("1.1.1.1", 53), ("8.8.8.8", 53),
    ("api.openai.com", 443), ("huggingface.co", 443)
  ]
  for each target:
    try asyncio.open_connection(host, port, timeout=2s)
    → record {target, result: "BLOCKED", latency_ms: None, ts: now()}
    except (timeout, ConnectionRefusedError, OSError):
    → record {target, result: "BLOCKED", latency_ms: elapsed, ts: now()}

  IF any result == "REACHED":
    → raise a SOVEREIGNTY_BREACH: log CRITICAL, set breach field, DO NOT halt
      (the demo must continue; the red banner in M1 is the response)

GET /sentinel/status — returns SovereigntyStatus:
<paste 04_INTEGRATION_CONTRACTS.md §6.3 verbatim>

The `bytes_egressed` counter is always 0 (we never make a successful connection);
the `attempts` and `blocked` counters increment every probe cycle.
`models` list is populated by calling GET http://ollama:11434/api/tags at startup.
`breach` is null unless a SOVEREIGNTY_BREACH was detected.

CONSTRAINTS — ≤ 150 lines, fully typed, no `any`. This service is on screen during
the pitch — the response shape must match §6.3 exactly or M1's ProofPanel breaks.
Output the file + 3 lines on what to wire next.
```

### P5 — Latency benchmark + hardware profiles

```
Senior DevOps/AI engineer. Python 3.11, httpx, pandas. AIR-GAPPED.

Create exactly one file: bench/latency.py  (≤ 150 lines)

A benchmarking script that measures the full AEGIS-WB latency stack.

Measure and report (10 runs each, median and p95):
  1. time-to-first-token (TTFT): POST /chat/sessions/{id}/messages → first `token` SSE frame
  2. total-turn-latency: from POST to `done` SSE frame
  3. embedding latency: POST /documents (40 MB PDF) → status READY
  4. retrieval-only latency: issue a query tagged as DOC_QA, measure from POST to `sources` frame

Output:
  - A Markdown table to stdout
  - bench/results_{hardware_profile}_{timestamp}.json

Pass --profile A|B|C on the command line. Profile C uses CPU-only (no GPU flag).

Also create docs/HARDWARE_PROFILES.md documenting the recommended Ollama settings for:
  Profile A: ≥ 16 GB VRAM (RTX 3090/4080/A4000):
    model=llama3.1:8b-instruct-q4_K_M, num_gpu=35, num_ctx=4096, num_batch=512
  Profile B: 8–16 GB VRAM (RTX 3060/4060):
    model=llama3.1:8b-instruct-q4_K_M, num_gpu=20, num_ctx=2048, num_batch=256
  Profile C: CPU only (≥ 32 GB RAM):
    model=llama3.1:8b-instruct-q2_K, num_gpu=0, num_ctx=2048, ENABLE_RERANKER=false

CONSTRAINTS — bench/latency.py ≤ 150 lines, no `any`. Output both files.
```

### P6 — Demo script

```
You are a technical pitch coach and senior engineer for a national hackathon (SIH).
Our product is AEGIS-WB (SIH26117): an air-gapped, agentic, multimodal AI workbench.

Create exactly one file: docs/DEMO_SCRIPT.md

A beat-by-beat 6-minute demo script for the judges' presentation. Structure:

Minute 0:00–0:45 — Opening hook
  Speak: one sentence on the problem (no cloud AI on confidential industrial data).
  Show: the sovereignty proof panel — "0 BYTES EGRESSED" prominently visible.
  Speak: "Everything you are about to see is running on this laptop."

Minute 0:45–2:00 — Document upload + ingestion
  Action: drag turbine_om_manual.pdf + T4_incident_report.pdf into the upload panel.
  Show: the live ingest progress bar (M1's P3 feature).
  Speak: "The documents never leave this machine. The model is local. The database is local."

Minute 2:00–3:30 — The main demo query (D6 differentiator)
  Type: "Why did Turbine-4 trip on 14 August? Give me the root cause."
  Show: the agent reasoning trace expanding live (M1's P4 ReasoningTrace).
  Show: the sources rail populating with page numbers.
  Show: the final answer with clickable citation [2] → PDF opens at page 42, highlighted.
  Speak: "The agent decomposed the question into 4 sub-queries, joined the CSV and the manual,
          and ranked three hypotheses by evidence. Single-shot RAG cannot do this."

Minute 3:30–4:15 — RBAC demo (D2 differentiator)
  Switch to the VIEWER persona (clearance 0).
  Ask the same question.
  Show: different answer, restricted documents absent from sources rail.
  Speak: "The filter is inside the vector query. The restricted content was never in the prompt."

Minute 4:15–5:00 — Human-in-the-loop (D7 differentiator)
  Ask: "Delete the incident report."
  Show: the approval card pausing the agent.
  Click Deny. Show the graph ending cleanly. Show the audit log entry.
  Speak: "The agent cannot act unilaterally on high-risk operations."

Minute 5:00–5:45 — Audit chain (D4 differentiator)
  Navigate to the audit page. Click "Verify chain".
  Show: "Chain valid. 847 entries. 0 breaks."
  Speak: "Every query, every retrieval, every approval — tamper-evident, non-repudiable."

Minute 5:45–6:00 — Close
  Return to proof panel: "0 BYTES EGRESSED. 4127 attempts blocked."
  Speak: "This is not a claim. It is an architectural guarantee."

For each beat also include:
- WHAT TO HAVE OPEN (windows, tabs, terminal position)
- FALLBACK PLAN if something fails (e.g., Ollama is slow → switch to Profile C settings)
- EXACT PROMPT TEXT to type (so any team member can drive)
```

---

## Contracts you author and must not break

- `04_INTEGRATION_CONTRACTS.md §6.2` — `OllamaClient` interface. M4 and M5 both import it.
  Any signature change is a CCR. In particular, `stream()` must return `AsyncIterator[str]`,
  not a coroutine that returns a list — M3's SSE endpoint drains it token by token.
- `04_INTEGRATION_CONTRACTS.md §6.3` — `SovereigntyStatus` JSON shape. M1's `ProofPanel`
  polls this every 5 s. Wrong field names silently break the panel during the pitch.
- `01_ALGORITHMS.md §3.1` — network topology. The 4-network layout with `internal: true`
  is the security proof. Changing it to a single shared bridge for "simplicity" destroys
  differentiator D1. Any change to this topology requires all 6 members to sign off.
- `Makefile` targets `make up`, `make down`, `make seed`, `make mock`, `make types`,
  `make backup`, `make restore` — M3's brief references these by name. They must exist
  and work from a clean clone with no manual steps.

## Your definition of done, every phase

```
□ `make up` starts all services from a clean clone, 0 manual steps, 0 crash-loops
□ Every service has a working healthcheck; `docker compose ps` shows all "healthy"
□ `bench/latency.py` p95 TTFT ≤ 2.5 s on the demo hardware (measured, not estimated)
□ `pytest tests/security/test_no_egress.py` passes — TCP to 1.1.1.1:53 fails from api/worker/ollama
□ Sentinel panel shows `reached: 0` after 10 minutes of uptime
□ Model digests in `models.lock` match `ollama list` output exactly
□ `OLLAMA_KEEP_ALIVE=-1` verified: TTFT after 10-min idle stays ≤ 3 s
□ `make seed` populates the demo corpus in < 3 min deterministically on a clean stack
□ `make backup && make restore` round-trips the DB and vector store without data loss
□ `docs/DEMO_SCRIPT.md` committed; 3 full dress rehearsals completed without crash
□ Reviewed by M3 (network/audit paths) and M1 (OllamaClient + sovereignty status shape)
```
