# AEGIS-WB Evaluation Results

Ran inside the live `api` container against real Postgres / Qdrant / Ollama
(no stubs, no mocked services). Datasets live in `data_pipeline/eval/`.

Date run: 2026-09-06

## Router accuracy — `eval/router_eval.py`
`AEGIS_EVAL_DATA_DIR=/tmp/eval` (60 held-out cases)

| intent       | score |
|--------------|-------|
| CHITCHAT     | 10/10 (1.0000) |
| COMPLIANCE   | 10/10 (1.0000) |
| DATA_ANALYSIS| 10/10 (1.0000) |
| DOC_QA       | 10/10 (1.0000) |
| INCIDENT     | 10/10 (1.0000) |
| VISION       | 9/10 (0.9000) |
| **overall**  | **59/60 (0.9833)** |

Accepted miss `router-020` (no image indicators in the question itself).

## RAG retrieval — `eval/rag_eval.py`
`ground_truth.jsonl` 71 cases (51 answerable), live corpus (748 chunks).

- recall@10 (doc or snippet): **0.6667** (34/51)
- precision@5: **0.4039**
- MRR@10: **0.6078**
- exact-snippet hit@10: **0.5098** (26/51)

Top retrieved docs: vibration_readings.csv 377, incident-report PDF 60,
equipment_failures.csv 32, maintenance_schedule.csv 24, spare_parts.csv 9,
OSHA_3071.pdf 5, OSHA_3132.pdf 3. Corpus is CSV-heavy; the vibration table
dominates retrievals.

## Groundedness (served traffic) — `eval/groundedness.py`
16 stored assistant turns actually served through the web:
- grounded 14/16 (0.875), abstained 2/16 (0.125)
- citation coverage mean=1.000 median=1.000 (n=14)
- latency mean=54.2s median=47.8s; tokens_out mean=105.9
- intent mix: DATA_ANALYSIS 6, COMPLIANCE 5, INCIDENT 4, VISION 1

## Ingest benchmark — `eval/ingest_bench.py`
- docs indexed 7/7 READY; chunks 748; qdrant points 748; bytes 11,115,847
- `ds_*` materialised tables: 4
- embed throughput (bge-m3): 100 texts in 35.7s → 2.8 docs/s

## DATA_ANALYSIS (SQL) verification
Live SQL over materialised tables, real numbers:
- TURBINE-04 failures = 31 (ds_equipment_failures, 565 rows)
- TURBINE-01 avg vibration = 2.284 (ds_vibration_readings, 51,840 rows)
- spare parts cost > 100 = 5 (ds_spare_parts, 12 rows)
- avg downtime TURBINE-01 this quarter = 235.909 … minutes (confirmed in chat answer)

## Tests
`backend/tests/` full suite: 37 passed (incl. test_csv_sql.py: materializer +
day-first timestamp normalisation + SQL guards; test_router.py: 60-case router
accuracy ≥ 0.95 + targeted routing).