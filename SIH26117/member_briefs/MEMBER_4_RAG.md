# MEMBER 4 — AI & RAG Engineer
### SIH26117 · Personal Brief · v1.0

**Read with:** `01_ALGORITHMS.md §1` (your algorithm, in full) and
`04_INTEGRATION_CONTRACTS.md §5, 6.1, 6.4` (your contracts).

---

## Your mandate

You build the system's memory. Every answer the workbench gives is only as good as the chunk you
retrieved, so retrieval quality is the ceiling on the entire project's demo. Two things are yours
and nobody else's: **how documents become chunks**, and **how a question finds the right chunk**.

**You own:** `backend/services/ingest/`, `backend/services/rag/`, `backend/worker/`,
`eval/{rag_eval,ingest_bench}.py`.

---

## Phase deliverables

| Phase | Build | Done when |
|---|---|---|
| **P1** | Qdrant container + collection `aegis_bge_m3_1024` with **payload indexes on `clearance_level`, `department`, `document_id`, `status`, `chunk_type`, `page_start`** created by a migration script. Embedding smoke test asserting dim == 1024. ARQ worker skeleton. Freeze the Chunk payload contract with M3/M5 | `python -m services.rag.smoke` embeds and retrieves inside the container |
| **P2** | The text pipeline end to end: PyMuPDF parser with bbox retention → Docling structurer → **layout-aware semantic chunker** → batched embedder → idempotent upsert (`uuid5` ids) → `self_test`. Retriever v1 (dense top-20) | M2's 50-doc corpus ingests in one command; factual questions hit the right chunk in the top 3 |
| **P3** | OCR path: PaddleOCR PP-OCRv4 + 300 DPI upscale + deskew/denoise, decided **per page** by text density and alpha ratio. Image path: OCR + VLM caption + kind classification as two independent chunk types. Tabular path: profile → real Postgres table + embedded data card + per-entity slices | A 30-page scanned manual becomes searchable; an image's caption and OCR text are both retrievable |
| **P4** | Advanced retrieval: multi-query expansion (3 paraphrases), BM25 sparse vectors, **RRF fusion**, `bge-reranker-v2-m3` cross-encoder with a 0.30 floor, MMR de-dup, parent-chunk expansion. Publish `search()` and `sql_query()` to M5 — **with no filter parameter in the signature** | `rag_eval.py`: recall@10 ≥ 0.85; precision@5 measurably better with the reranker on |
| **P5** | Integrate `build_acl_filter()` so **every** search is pre-filtered; implement `acl_reverify()` against live Postgres labels with `SECURITY_ANOMALY` emission (paired with M3). Provenance service resolving chunk → `{document_id, title, page, bbox, snippet}`. Relabel/re-index path | `test_prefilter_not_postfilter.py` and `test_stale_payload.py` pass; every citation resolves to a real page and box |
| **P6** | `int8` quantisation with `always_ram`, HNSW `m`/`ef_construct` tuning, embedding batch-size sweep, parallel OCR, warm caches. Publish the retrieval ablation table (±hybrid, ±reranker, ±breadcrumbs) — it becomes a pitch slide | 100-page text PDF ≤ 90 s; retrieval p95 ≤ 400 ms; ablation committed |

## Your seven technical problems

1. **Where to split.** Character-count chunking severs a warning from its procedure and a torque
   value from its unit. Respect headings, keep tables atomic, prepend the heading breadcrumb. This
   single decision moves recall more than any model choice you will make.
2. **Oversized tables.** A 300-row spec table is neither one chunk nor 300 fragments: split by rows
   and **repeat the header** in every fragment.
3. **The OCR boundary is per page, not per document.** Real manuals mix digital and scanned pages,
   and some have a *broken* text layer that extracts as ligature garbage — hence the `alpha_ratio`
   guard alongside character density.
4. **Never embed CSV rows.** Embed a data card plus per-entity roll-up slices; row-level questions
   are answered by SQL through M5's tool.
5. **Idempotency under retry.** `uuid5(document_id:chunk_index)` ids, and delete-by-`document_id`
   before re-ingest. Without this one retry silently doubles the corpus and quality quietly rots.
6. **Reranker cost.** A cross-encoder scores every candidate. Cap at 20, batch on GPU, and keep
   `ENABLE_RERANKER` a flag so Profile C hardware still works.
7. **Dense search cannot do exact match.** "E-4471" and "SKF-6206-2RS" are where embeddings fail
   and BM25 wins. Hybrid + RRF is mandatory for an industrial corpus, not a nice-to-have.


---

## Ready-to-paste AI prompts

Paste the referenced contract section **verbatim** with each prompt. One file per request.

### P1 — Qdrant collection + migration script

```
You are a senior AI/RAG engineer. Stack: Python 3.11, qdrant-client 1.9, Docker.
This system is AIR-GAPPED: Qdrant runs locally in Docker; no cloud instance.

Create exactly one file: backend/services/rag/migrations/create_collection.py  (≤ 120 lines)

It must:
1. Connect to Qdrant at settings.qdrant_url (default http://qdrant:6333).
2. Create (or skip-if-exists) the collection: aegis_bge_m3_1024
   - Dense vector: name="dense", size=1024, distance=Cosine
   - Sparse vector: name="bm25"
   - Quantization: scalar int8, always_ram=True
3. Create payload indexes on EXACTLY these fields (required for fast pre-filtering):
   clearance_level : integer
   department      : keyword
   document_id     : keyword  (uuid stored as string)
   status          : keyword
   chunk_type      : keyword
   page_start      : integer
4. Run a smoke test: embed the string "smoke test", upsert 1 point, retrieve by id,
   assert dim == 1024, delete the point. Print PASS or raise on failure.

CONSTRAINTS
- Idempotent: running twice must not crash or duplicate anything.
- All settings from core.config — never hardcode URLs or credentials.
- ≤ 120 lines, fully typed, no `any`.
Output the complete file, then 3 lines on what to wire next.
```

### P2 — Text pipeline end-to-end

```
Senior AI/RAG engineer. Python 3.11, PyMuPDF (fitz), Docling, qdrant-client 1.9,
sentence-transformers (BGE-M3 via Ollama). AIR-GAPPED.

Create exactly one file: backend/services/ingest/pdf_parser.py  (≤ 200 lines)

Implements Stage 2a from 01_ALGORITHMS.md §1.3 — per-page OCR decision:

TEXT_DENSITY_FLOOR = 120   # chars of extractable text per page
ALPHA_RATIO_FLOOR  = 0.55  # guard against ligature garbage from broken embedded fonts

async def parse(blob: bytes, doc: DocumentRow) -> list[Element]:
  For each page:
    - Extract text dict with fitz (keeps bbox per span)
    - If len(text) >= TEXT_DENSITY_FLOOR AND alpha_ratio(text) >= ALPHA_RATIO_FLOOR:
        → elements_from_layout(raw, pno)   # keeps bbox for PDF citation highlighting
      else:
        → upscale page to 300 DPI pixmap, deskew, denoise, grayscale
        → await ocr.extract(img, pno)      # PaddleOCR PP-OCRv4
        → append Element(kind="OCR_NOTE", page=pno, text="[page reconstructed via OCR]")
    - Extract tables via Docling (pdfplumber fallback if Docling fails)
    - Append figure placeholders for every embedded image

Return list[Element] where Element has: kind, page, text, bbox, font_size, heading_level.

ALPHA_RATIO: proportion of chars in string.ascii_letters. A ratio < 0.55 means the
"text" is mostly ligature garbage from a broken embedded font — treat as scanned.

CONSTRAINTS
- ≤ 200 lines. OCR is async (awaitable); PyMuPDF calls go through run_in_threadpool.
- Fully typed, no `any`. Never load the whole PDF into RAM — stream via blob bytes.
Output the file, then 3 lines on what to wire next.
```

### P3 — Semantic chunker

```
Senior AI/RAG engineer. Python 3.11, tiktoken (cl100k_base tokenizer).

Create exactly one file: backend/services/ingest/chunker.py  (≤ 180 lines)

Implements the layout-aware semantic chunker from 01_ALGORITHMS.md §1.5.

TARGET, MAX, OVERLAP = 512, 640, 64   # tokens

def split(tree: DocTree, doc: DocumentRow) -> list[Chunk]:

Rules (implement in this exact priority order):
  R1 — Atomic blocks (TABLE, FIGURE, CODE, FORMULA) are never split.
       Oversized tables split by ROW — REPEAT the header row in every fragment.
  R2 — A heading change at H1 or H2 flushes the current chunk buffer (semantic boundary).
  R3 — Accumulate nodes until MAX tokens, then flush. Overlap = last OVERLAP tokens
       of the flushed chunk, only within the same section — never across an H1/H2 break.

def decorate(chunk: Chunk, doc: DocumentRow) -> Chunk:
  Prepend heading breadcrumb to embed_text:
    "[{doc.title} › {' › '.join(chunk.heading_path)}]\n{chunk.text}"
  Set page_start, page_end from the constituent nodes.
  Set bbox_union = bounding union of all node bboxes on the same page.

Chunk output schema (frozen — matches 01_ALGORITHMS.md §1.5 exactly):
  id:            uuid5(NAMESPACE_OID, f"{doc.id}:{chunk_index}")   # deterministic
  document_id, chunk_index, text, embed_text, heading_path,
  chunk_type, page_start, page_end, bbox_union, token_count,
  clearance_level, department, checksum, ingested_at

CONSTRAINTS — ≤ 180 lines, fully typed, no `any`.
Fixed-size character splitting is BANNED. Output the file + 3 lines on wiring.
```

### P4 — Advanced retrieval: hybrid + reranker

```
Senior AI/RAG engineer. Python 3.11, qdrant-client 1.9, sentence-transformers, asyncio.

Create exactly one file: backend/services/rag/retriever.py  (≤ 200 lines)

Implements the public retrieval entry point consumed by M5's tools.

EXACT SIGNATURE (contractual — do not add parameters):
async def search(
    query: str,
    acl: models.Filter,           # built by build_acl_filter(). NOT caller-authored.
    *,
    k: int = 20,
    doc_ids: list[UUID] | None = None,   # narrowing only; cannot widen acl
    chunk_types: list[ChunkType] | None = None,
) -> list[RetrievedChunk]:

ALGORITHM (implement exactly — 01_ALGORITHMS.md §2.5 retrieval sub-routine):
1  variants = [query] + paraphrase(query, n=2)      # 3 total queries
2  dense  = union(qdrant.search(embed(v), filter=acl, limit=k) for v in variants)
3  sparse = qdrant.search(bm25_encode(query), filter=acl, limit=k)
4  fused  = RRF(dense, sparse)  →  score = Σ 1/(60 + rank_i)
5  top20  = fused[:20]                               # cap before reranker
6  IF settings.enable_reranker:
       scores = cross_encoder.predict([(query, h.text) for h in top20])   # batched
       top20  = [h for h,s in zip(top20, scores) if s >= 0.30]            # floor
       top20.sort(key=lambda x: x.rerank_score, reverse=True)
7  top20 = mmr_dedupe(top20, lambda_=0.7)            # marginal relevance de-dup
8  top20 = parent_expand(top20)                      # swap chunk → parent if exists
9  return [await acl_reverify(h, acl_labels) for h in top20]   # defence in depth

Also implement build_acl_filter(user: ServerUserContext) -> models.Filter in a
SEPARATE file: backend/services/rag/acl_filter.py  (≤ 90 lines)
Use must conditions: clearance_level lte user.clearance_level, status == READY,
department MatchAny(user.departments) — skip department for AUDITOR/ADMIN roles.
FAIL CLOSED: any missing or unknown claim denies.

CONSTRAINTS — ≤ 200 lines retriever, ≤ 90 lines acl_filter. Fully typed, no `any`.
Output both files, then 3 lines on what to wire next.
```

### P5 — Provenance service + ACL reverify

```
Senior AI/RAG engineer. Python 3.11, asyncpg, qdrant-client 1.9, Pydantic 2.7.

Create exactly one file: backend/services/rag/provenance.py  (≤ 150 lines)

Implements the provenance resolution service that turns a retrieved chunk_id into a
citation M1 can render as a highlighted PDF page.

async def resolve(chunk_ids: list[UUID], session: AsyncSession) -> list[Citation]:
  One SQL round-trip: SELECT * FROM chunk_refs WHERE id = ANY($1)
  Return list[Citation] where each Citation has:
    chunk_id, document_id, document_title, page, bbox, snippet (first 200 chars of text)
  For any chunk_id not found: log a WARNING, skip — never raise into the request path.

Also implement acl_reverify() in the SAME file:
async def acl_reverify(hits: list[Hit], user_ctx: ServerUserContext,
                        session: AsyncSession) -> list[Hit]:
  "Defence in depth — catches stale vector payloads after a re-classification."
  labels = await repo.get_labels({h.payload["document_id"] for h in hits})  # 1 SQL
  kept = []
  for h in hits:
      live = labels.get(h.payload["document_id"])
      if live is None or not can_read(user_ctx, live).allowed:
          audit.emit("SECURITY_ANOMALY", user=user_ctx, doc=h.payload["document_id"],
                     reason="stale_payload_or_revoked", severity="HIGH")
          continue                    # dropped BEFORE reaching the LLM
      kept.append(h)
  return kept

CONSTRAINTS — ≤ 150 lines, fully typed, no `any`.
A stale-payload drop must ALWAYS emit a SECURITY_ANOMALY audit event — never silently skip.
Output the file + 3 lines on wiring.
```

### P6 — Retrieval ablation table

```
Senior AI/RAG engineer. Python 3.11, pandas, scipy.

Create exactly one file: eval/rag_eval.py  (≤ 250 lines)

Runs a retrieval ablation study using M2's eval/ground_truth.jsonl.

For each configuration in the matrix:
  - dense-only
  - hybrid (dense + BM25 + RRF)
  - hybrid + reranker
  - hybrid + reranker + heading breadcrumbs

Compute and print for each config:
  recall@10, precision@5, MRR@10, mean_latency_ms, p95_latency_ms

REQUIREMENTS
- Use the live retriever (import from services.rag.retriever) — not a mock.
- Run evaluation under the MAINTENANCE/ENGINEER persona (clearance=2) so ACL
  filtering is exercised and does not distort recall.
- Output a Markdown table to stdout and a machine-readable eval/ablation_results.json.
- The table must be committed and becomes a slide in the pitch deck.

CONSTRAINTS — ≤ 250 lines, deterministic (same seed on every run), no `any`.
The recall@10 target is ≥ 0.85. Flag FAIL in the output if it is not met.
```

---

## Contracts you must honour exactly

- `04_INTEGRATION_CONTRACTS.md §5` — the Qdrant payload schema. Every field is required.
  `page_start` not `page`. `bbox_union` not `bbox`. `chunk_type` not `type`. One wrong
  name and M5's tool will silently drop the citation and M1's PDF highlight will never appear.
- `04_INTEGRATION_CONTRACTS.md §6.1` — the `search()` signature. **No `filter` parameter,
  no `clearance` parameter.** This is a security contract, not a convenience choice.
- `04_INTEGRATION_CONTRACTS.md §3` — `sources` frame field names. `page_start` not `page`.
  `bbox_union` in the sources frame; `bbox` (resolved, per-page) in the citations frame.
  M3 assembles these from your `RetrievedChunk` — the field names must match exactly.
- `chunk_refs.id == Qdrant point id`. Both are `uuid5(NAMESPACE_OID, f"{doc_id}:{idx}")`.
  If you generate them independently in the two systems, `acl_reverify()` cannot join them
  and every citation lookup silently fails.

## Your definition of done, every phase

```
□ Runs inside docker compose (not just locally with a local Qdrant)
□ ≤ 300 LOC per file; chunker.py ≤ 180; acl_filter.py ≤ 90
□ mypy clean, no `any`
□ python -m services.rag.smoke passes inside the container
□ M2's 50-doc corpus ingests in one command with 0 FAILED documents
□ Qdrant point id == chunk_refs.id for every chunk — verified by the self_test()
□ acl_reverify() ALWAYS emits SECURITY_ANOMALY on a stale-payload drop
□ ENABLE_RERANKER=false still works (Profile C hardware fallback)
□ rag_eval.py recall@10 ≥ 0.85 printed and committed to eval/ablation_results.json
□ Ablation table committed — it becomes a pitch slide
□ Reviewed by M3 (acl_filter paths) and M5 (tool signature)
```
