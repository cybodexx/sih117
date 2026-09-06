.PHONY: up up-dev down logs build seed mock types test lint bench demo smoke backup restore check-loc pull-models

# === Development ===
up:
	docker compose up -d --build

up-dev:
	docker compose up -d --build api web worker sentinel postgres redis qdrant ollama

down:
	docker compose down

logs:
	docker compose logs -f

build:
	docker compose build

# === Mock server (for M1/M5 to develop against before Day 2) ===
mock:
	python -m uvicorn backend.main:app --reload --port 8001

# === Models ===
pull-models:
	docker compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M
	docker compose exec ollama ollama pull llava:7b-v1.6
	docker compose exec ollama ollama pull bge-m3

# === Types generation ===
types:
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o lib/types.gen.ts

# === Database ===
seed:
	python -m data_pipeline.collect.normalise
	docker compose exec api python -m alembic upgrade head

migrate:
	docker compose exec api python -m alembic revision --autogenerate -m "$(msg)"
	docker compose exec api python -m alembic upgrade head

# === Testing ===
test:
	pytest backend/tests/ -v --tb=short

lint:
	ruff check backend/
	mypy backend/
	cd frontend && npx tsc --noEmit

smoke:
	@echo "Running smoke test..."
	python -c "import httpx; r=httpx.get('http://localhost:8000/health'); assert r.status_code==200; print('API: OK')"
	python -c "import httpx; r=httpx.get('http://localhost:3000'); print(f'Web: {r.status_code}')"
	python -c "import httpx; r=httpx.get('http://localhost:6333/readyz'); print(f'Qdrant: {r.status_code}')"
	python -c "import httpx; r=httpx.get('http://localhost:11434/api/tags'); print(f'Ollama: {r.status_code}')"

# === Benchmarks ===
bench:
	python bench/latency.py --profile B

# === Demo ===
demo:
	@echo "Starting demo..."
	docker compose -f docker-compose.yml -f docker-compose.airgap.yml up -d
	@echo "Stack running. Follow docs/DEMO_SCRIPT.md"

# === Backup ===
backup:
	docker compose exec postgres pg_dump -U aegis aegis_wb > backup_%DATE:~0,4%%DATE:~5,2%%DATE:~8,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%.sql

restore:
	docker compose exec -T postgres psql -U aegis aegis_wb < $(file)

# === LOC gate ===
check-loc:
	python tools/check_loc.py
