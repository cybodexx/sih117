"""Normalise and deduplicate collected documents.

Usage: python -m data_pipeline.collect.normalise
Produces: manifest.jsonl with document metadata.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

SEED_DIR = Path("data_pipeline/seed")
MANIFEST = SEED_DIR / "manifest.jsonl"


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def normalise() -> int:
    """Walk seed/, dedupe by hash, emit manifest.jsonl."""
    seen: set[str] = set()
    entries: list[dict] = []
    count = 0

    for subdir in ["public", "internal", "confidential", "restricted"]:
        base = SEED_DIR / subdir
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir() or p.suffix in (".yaml", ".md", ".jsonl"):
                continue
            digest = compute_sha256(p)
            if digest in seen:
                continue
            seen.add(digest)
            entries.append({
                "filename": p.name,
                "path": str(p.relative_to(SEED_DIR)),
                "clearance": subdir,
                "checksum": digest,
                "size_bytes": p.stat().st_size,
            })
            count += 1

    with open(MANIFEST, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")

    print(f"Normalised {count} documents, manifest written to {MANIFEST}")
    return count


if __name__ == "__main__":
    normalise()
