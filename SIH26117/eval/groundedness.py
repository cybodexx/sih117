"""Groundedness evaluation over real stored assistant messages.

Computes grounded rate, citation coverage, abstain rate, and latency statistics
from the production message table. No synthetic data — everything reported has
actually been served to users.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from collections import Counter

from sqlalchemy import select

from backend.db.base import async_session
from backend.db.models.message import ChatMessageModel


async def main() -> None:
    async with async_session() as db:
        result = await db.execute(select(ChatMessageModel).where(ChatMessageModel.role == "assistant"))
        msgs = result.scalars().all()

    grounded = [m for m in msgs if bool(m.grounded)]
    abstained = [m for m in msgs if bool(m.abstained)]
    intents = Counter(str(m.intent) for m in msgs)

    coverages = []
    for m in grounded:
        citations = m.citations or []
        sources = m.sources or []
        if sources:
            coverages.append(len(citations) / len(sources))
        elif len(citations) == 0:
            coverages.append(0.0)

    latencies = [int(m.latency_ms or 0) for m in msgs if m.latency_ms]
    tokens_out = [int(m.tokens_out or 0) for m in msgs if m.tokens_out]

    print(f"assistant messages stored: {len(msgs)}")
    print(f"  grounded : {len(grounded)} ({len(grounded)/max(len(msgs),1):.3f})")
    print(f"  abstained: {len(abstained)} ({len(abstained)/max(len(msgs),1):.3f})")
    if coverages:
        print(f"  citation coverage  mean={statistics.mean(coverages):.3f} "
              f"median={statistics.median(coverages):.3f} (n={len(coverages)})")
    if latencies:
        print(f"  latency_ms mean={statistics.mean(latencies):.0f} median={statistics.median(latencies):.0f}")
    if tokens_out:
        print(f"  tokens_out mean={statistics.mean(tokens_out):.1f}")
    print("  intent distribution:", dict(intents.most_common()))


if __name__ == "__main__":
    asyncio.run(main())