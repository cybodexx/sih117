"""AEGIS-WB Latency Benchmark.

Measures TTFT (time-to-first-token), total turn latency, and embedding latency.
Outputs both a markdown table and a JSON file.

Usage:
    python bench/latency.py --profile A
    python bench/latency.py --profile B --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

PROFILES = {
    "A": {
        "label": "Full stack (ollama + qdrant + postgres)",
        "base_url": "http://localhost:8000",
        "embed_url": "http://localhost:11434",
        "tests": ["ttft", "turn", "embed"],
    },
    "B": {
        "label": "API only (mock agent, no LLM)",
        "base_url": "http://localhost:8000",
        "embed_url": None,
        "tests": ["ttft", "turn"],
    },
    "C": {
        "label": "Embedding latency only",
        "base_url": None,
        "embed_url": "http://localhost:11434",
        "tests": ["embed"],
    },
}

SAMPLE_EMBED_TEXTS = [
    "The turbine trip was caused by excessive vibration at 7.1 mm/s RMS.",
    "Monthly maintenance schedule requires inspection of all bearing assemblies.",
    "Boiler tube failure analysis indicates corrosion in the waterwall section.",
    "Generator stator temperature exceeded 105 degrees Celsius during peak load.",
    "Coal mill gearbox vibration levels are within acceptable limits.",
]


@dataclass
class BenchResult:
    test: str
    elapsed_ms: float
    detail: str = ""
    ok: bool = True
    raw: dict[str, Any] = field(default_factory=dict)


def _create_session(base_url: str, http: httpx.Client) -> str:
    resp = http.post(
        f"{base_url}/api/v1/chat/sessions",
        json={"title": "Benchmark Session"},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _measure_ttft(base_url: str, http: httpx.Client) -> BenchResult:
    """Measure time-to-first-token from the SSE stream."""
    session_id = _create_session(base_url, http)

    post_resp = http.post(
        f"{base_url}/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "What is the vibration limit for turbine trip?"},
    )
    post_resp.raise_for_status()
    turn_id = post_resp.json()["turn_id"]

    t0 = time.perf_counter()
    first_token_ms: float | None = None
    tokens: list[str] = []

    with http.stream(
        "GET",
        f"{base_url}/api/v1/chat/sessions/{session_id}/stream",
        params={"turn_id": turn_id},
    ) as stream_resp:
        stream_resp.raise_for_status()
        event_type = ""
        for raw_line in stream_resp.iter_lines():
            if raw_line.startswith("event: "):
                event_type = raw_line[7:].strip()
                continue
            if not raw_line.startswith("data: "):
                continue
            data_str = raw_line[6:]
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if event_type == "token" and first_token_ms is None:
                first_token_ms = (time.perf_counter() - t0) * 1000
                tokens.append(data.get("delta", ""))
            elif event_type == "token":
                tokens.append(data.get("delta", ""))
            elif event_type == "done":
                break

    total_ms = (time.perf_counter() - t0) * 1000
    if first_token_ms is None:
        return BenchResult(
            test="TTFT",
            elapsed_ms=total_ms,
            detail="No token event received",
            ok=False,
            raw={"turn_id": turn_id},
        )
    return BenchResult(
        test="TTFT",
        elapsed_ms=round(first_token_ms, 1),
        detail=f"first token after {len(tokens)} tokens, total {round(total_ms, 1)} ms",
        raw={"turn_id": turn_id, "token_count": len(tokens)},
    )


def _measure_turn(base_url: str, http: httpx.Client) -> BenchResult:
    """Measure total turn latency (POST message -> done event)."""
    session_id = _create_session(base_url, http)

    post_resp = http.post(
        f"{base_url}/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "List all active alarms on unit 3."},
    )
    post_resp.raise_for_status()
    turn_id = post_resp.json()["turn_id"]

    t0 = time.perf_counter()
    done_payload: dict[str, Any] = {}

    with http.stream(
        "GET",
        f"{base_url}/api/v1/chat/sessions/{session_id}/stream",
        params={"turn_id": turn_id},
    ) as stream_resp:
        stream_resp.raise_for_status()
        event_type = ""
        for raw_line in stream_resp.iter_lines():
            if raw_line.startswith("event: "):
                event_type = raw_line[7:].strip()
                continue
            if not raw_line.startswith("data: "):
                continue
            data_str = raw_line[6:]
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            if event_type == "done":
                done_payload = data
                break

    total_ms = (time.perf_counter() - t0) * 1000
    server_ms = done_payload.get("latency_ms", 0)
    return BenchResult(
        test="TURN",
        elapsed_ms=round(total_ms, 1),
        detail=f"client {round(total_ms, 1)} ms, server {server_ms} ms",
        raw=done_payload,
    )


def _measure_embed(base_url: str, http: httpx.Client) -> BenchResult:
    """Measure embedding latency via Ollama /api/embeddings."""
    payload = {"model": "bge-m3", "input": SAMPLE_EMBED_TEXTS}
    t0 = time.perf_counter()
    resp = http.post(f"{base_url}/api/embeddings", json=payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    if resp.status_code != 200:
        return BenchResult(
            test="EMBED",
            elapsed_ms=round(elapsed_ms, 1),
            detail=f"HTTP {resp.status_code}: {resp.text[:200]}",
            ok=False,
        )

    data = resp.json()
    embeddings = data.get("embeddings", [])
    dims = [len(e) for e in embeddings] if embeddings else []
    return BenchResult(
        test="EMBED",
        elapsed_ms=round(elapsed_ms, 1),
        detail=f"{len(embeddings)} vectors, dims={dims}",
        raw={"count": len(embeddings), "dims": dims},
    )


def _render_markdown(results: list[BenchResult], profile_name: str) -> str:
    lines = [
        f"# AEGIS-WB Latency Benchmark — Profile {profile_name}",
        "",
        "| Test | Latency (ms) | OK | Detail |",
        "|------|-------------|----|--------|",
    ]
    for r in results:
        ok_mark = "✓" if r.ok else "✗"
        lines.append(
            f"| {r.test} | {r.elapsed_ms} | {ok_mark} | {r.detail} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="AEGIS-WB latency benchmark")
    parser.add_argument(
        "--profile",
        choices=list(PROFILES),
        default="B",
        help="Test profile: A (full), B (API only), C (embed only)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Override API base URL",
    )
    parser.add_argument(
        "--output",
        default="bench/results.json",
        help="Path for JSON output",
    )
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    base_url = args.base_url or profile["base_url"]
    embed_url = profile["embed_url"]
    tests = profile["tests"]

    print(f"Profile {args.profile}: {profile['label']}")
    print(f"API: {base_url}  |  Embed: {embed_url}")
    print()

    results: list[BenchResult] = []
    http = httpx.Client(timeout=30.0)

    try:
        if "ttft" in tests and base_url:
            print("Running TTFT benchmark...")
            results.append(_measure_ttft(base_url, http))
            print(f"  -> {results[-1].elapsed_ms} ms ({results[-1].ok})")

        if "turn" in tests and base_url:
            print("Running TURN benchmark...")
            results.append(_measure_turn(base_url, http))
            print(f"  -> {results[-1].elapsed_ms} ms ({results[-1].ok})")

        if "embed" in tests and embed_url:
            print("Running EMBED benchmark...")
            results.append(_measure_embed(embed_url, http))
            print(f"  -> {results[-1].elapsed_ms} ms ({results[-1].ok})")
    finally:
        http.close()

    md = _render_markdown(results, args.profile)
    print()
    print(md)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "profile": args.profile,
                "profile_label": profile["label"],
                "results": [
                    {
                        "test": r.test,
                        "elapsed_ms": r.elapsed_ms,
                        "ok": r.ok,
                        "detail": r.detail,
                        "raw": r.raw,
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nJSON written to {output_path}")

    if any(not r.ok for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
