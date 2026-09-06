"""RAG evaluation — recall@10, precision@5, MRR@10 over ground_truth.jsonl.

Runs the real retriever against the live Qdrant corpus, then scores how often
the ground-truth source document is retrieved. Also reports token-level hit
rate (the exact_snippet appearing inside a retrieved chunk).
"""
from __future__ import annotations

import asyncio
import os
import json
import statistics
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from backend.core.rbac import MAX_CLEARANCE, Role, ServerUserContext
from backend.db.base import async_session
from backend.db.models.document import DocumentModel
from backend.services.rag.retriever import search

_DATA_DIR = Path(os.environ.get("AEGIS_EVAL_DATA_DIR", Path(__file__).resolve().parent.parent / "data_pipeline" / "eval"))
GT_FILE = _DATA_DIR / "ground_truth.jsonl"


def _admin() -> ServerUserContext:
    return ServerUserContext(
        user_id="eval-admin", role=Role.ADMIN,
        clearance_level=MAX_CLEARANCE[Role.ADMIN], departments=["*"],
    )


async def _doc_filename_map() -> dict[str, str]:
    async with async_session() as db:
        result = await db.execute(select(DocumentModel))
        return {str(d.id): d.filename for d in result.scalars().all()}


async def main() -> None:
    if not GT_FILE.exists():
        raise SystemExit(f"missing {GT_FILE} — run data_pipeline.eval.build_ground_truth first")
    cases = [json.loads(line) for line in GT_FILE.open(encoding="utf-8")]
    filenames = await _doc_filename_map()

    answerable = [c for c in cases if c.get("answerable") is not False]
    doc_coverage: Counter[str] = Counter()
    sem = asyncio.Semaphore(3)

    async def _score_one(case: dict) -> dict[str, object]:
        async with sem:
            question = case["question"]
            snippets = [(case.get("source_file") or ""), (case.get("exact_snippet") or "").strip()]
            chunks = await search(question, _admin(), k=10)
        src, snippet = snippets
        relevant: list[bool] = []
        for c in chunks:
            fname = filenames.get(c.document_id, "")
            doc_coverage[fname] += 1
            if src and fname == src:
                relevant.append(True)
            elif snippet and snippet.lower() in (c.text or "").lower():
                relevant.append(True)
            else:
                relevant.append(False)
        rank = _rank_of_first(relevant)
        return {
            "has_relevant": any(relevant),
            "rank": rank,
            "top5": relevant[:5],
            "snippet_found": bool(snippet) and any(
                snippet.lower() in (c.text or "").lower() for c in chunks
            ),
        }

    results = await asyncio.gather(*[_score_one(c) for c in answerable])

    recall_hits = []
    precision5 = []
    mrrs = []
    snippet_hit = 0
    for r in results:
        recall_hits.append(1.0 if r["has_relevant"] else 0.0)
        if r["rank"]:
            mrrs.append(1.0 / r["rank"])
        else:
            mrrs.append(0.0)
        top5 = [bool(x) for x in r["top5"]]
        precision5.append(sum(top5) / 5 if top5 else 0.0)
        if r["snippet_found"]:
            snippet_hit += 1

    n = len(answerable)
    with_src = sum(1 for c in answerable if c.get("source_file"))
    print(f"ground_truth.jsonl: {len(cases)} cases ({n} answerable, {len(cases)-n} unanswerable)")
    print(f"answerable with source_file: {with_src}/{n}")
    print(f"recall@10 (doc or snippet): {statistics.mean(recall_hits):.4f}  [{sum(recall_hits)}/{n}]")
    print(f"precision@5        : {statistics.mean(precision5):.4f}" if precision5 else "precision@5: n/a")
    print(f"MRR@10             : {statistics.mean(mrrs):.4f}" if mrrs else "MRR@10: n/a")
    print(f"exact-snippet hit@10: {snippet_hit}/{n} ({snippet_hit/n:.4f})")
    print("top-10 retrieved documents (coverage counts):")
    for fname, cnt in doc_coverage.most_common(10):
        print(f"  {cnt:4d}  {fname or '(unknown)'}")


def _rank_of_first(relevant: list[bool]) -> int | None:
    for i, ok in enumerate(relevant, start=1):
        if ok:
            return i
    return None


if __name__ == "__main__":
    asyncio.run(main())