"""Router evaluation — accuracy of the live intent classifier over router_cases.jsonl."""
from __future__ import annotations

import asyncio
import json
import os
from collections import Counter
from pathlib import Path

from backend.api.v1.chat_stream import _classify_intent

CASES_FILE = Path(os.environ.get(
    "AEGIS_EVAL_DATA_DIR", Path(__file__).resolve().parent.parent / "data_pipeline" / "eval"
)) / "router_cases.jsonl"


async def main() -> None:
    if not CASES_FILE.exists():
        raise SystemExit(f"missing {CASES_FILE} — run data_pipeline.eval.build_router_cases first")
    cases = [json.loads(line) for line in CASES_FILE.open(encoding="utf-8")]

    correct = 0
    per_intent = Counter()
    per_correct = Counter()
    misses: list[tuple[str, str, str, str]] = []

    for case in cases:
        question = case["question"]
        expected = case["intent"]
        predicted, _ = _classify_intent(question)
        per_intent[expected] += 1
        if predicted == expected:
            correct += 1
            per_correct[expected] += 1
        else:
            misses.append((case["id"], expected, predicted, question))

    total = len(cases)
    print(f"router_cases.jsonl: {total} cases")
    print(f"overall accuracy: {correct}/{total} ({correct/total:.4f})")
    for intent in sorted(per_intent):
        ok = per_correct[intent]
        n = per_intent[intent]
        print(f"  {intent:14s} {ok}/{n} ({ok/n:.4f})")
    print("misclassified:")
    for mid, exp, pred, q in misses:
        print(f"  {mid} expected={exp} got={pred} | {q}")


if __name__ == "__main__":
    asyncio.run(main())