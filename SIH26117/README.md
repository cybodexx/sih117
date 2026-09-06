# AEGIS-WB (SIH26117)

## Sovereign On-Premise Agentic AI Workbench

A fully air-gapped, multimodal, agentic AI workbench that runs on a single on-premise workstation for confidential industrial work.

### Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your settings (keys MUST match backend/core/config.py exactly)

# 2. Pull models (requires internet — one-time only)
docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
docker compose exec ollama ollama pull bge-m3
docker compose exec ollama ollama pull llava:7b-v1.6   # optional (vision/OCR)

# 3. Build images (backend sources, embedding pipeline, frontend)
docker compose build api worker web

# 4. Start the stack
docker compose up -d
# Migrations run automatically at API startup. Uploaded files, JWT keys and
# model-embedding pipelines share the `vault` volume.

# 5. Open
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# Sentinel (sovereignty probe): http://localhost:8001/sentinel/status
```

### Demo flow

1. Log in (`frontend/app/(auth)/login` — seeded account in the database).
2. Upload a PDF in the **Documents** tab → QUEUED → PROCESSING → READY.
3. Chat an answer in **Chat** → grounded, source-cited streaming response.
4. Check **Audit Log** (hash-chained trail) and **Sovereignty** (egress probe).

### Development

```bash
make mock      # Start mock server for frontend dev
make test      # Run tests
make lint      # Run linters
make smoke     # Health check all services
```

### Architecture

See `SIH26117/00_MASTER_SRS.md` for the full technical specification.

### Team

| Member | Focus | Owned Paths |
|--------|-------|-------------|
| M1 | Frontend / UI | `frontend/` |
| M2 | Data Engineer | `data_pipeline/` |
| M3 | Backend & Security | `backend/{api,core,db,schemas,services/{crypto,audit}}` |
| M4 | AI & RAG | `backend/{services/{ingest,rag},worker}` |
| M5 | Agentic Workflow | `backend/agents/` |
| M6 | Integration Lead | `docker-compose*, Makefile, tools/` |

### License

SIH26117 — Smart India Hackathon 2026
