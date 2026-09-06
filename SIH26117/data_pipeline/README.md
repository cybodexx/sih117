# AEGIS-WB Data Pipeline
# M2 owns this directory.

## Sources
# Sources.yaml: provenance register for every document in the corpus.
# Each entry: url, licence, retrieved_date, sha256, filename

## Corpus Layout
# seed/public/     — clearance 0, publicly available documents
# seed/internal/   — clearance 1, aggregated logs, trend data
# seed/confidential/ — clearance 2, manuals, failure logs, schematics
# seed/restricted/ — clearance 3, incident reports, audit trails

## Evaluations
# eval/ground_truth.jsonl — 120 Q&A pairs with exact source spans
# eval/adversarial_rbac.jsonl — 200 adversarial RBAC test cases
# eval/router_cases.jsonl — 60 labelled intent routing cases

## Scripts
# collect/normalise.py — dedupe, hash, emit manifest.jsonl
# synth/gen_failure_logs.py — generate realistic CSV datasets
