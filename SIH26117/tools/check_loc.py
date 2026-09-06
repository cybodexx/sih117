"""LOC gate — fail CI if any source file exceeds 300 lines."""
import sys
import pathlib

HARD = 300
WARN = 200
ROOTS = ["backend", "frontend", "data_pipeline", "eval", "tools"]
EXTS = {".py", ".ts", ".tsx"}
SKIP = {"node_modules", ".next", "__pycache__", "alembic/versions", ".venv", "dist", "types.gen.ts"}


def offenders() -> list[tuple[str, int]]:
    bad: list[tuple[str, int]] = []
    for root in ROOTS:
        root_path = pathlib.Path(root)
        if not root_path.exists():
            continue
        for p in root_path.rglob("*"):
            if p.suffix not in EXTS:
                continue
            if any(s in p.as_posix() for s in SKIP):
                continue
            if "/tests/" in p.as_posix():
                continue
            n = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
            if n > HARD:
                bad.append((p.as_posix(), n))
            elif n > WARN and p.suffix == ".tsx":
                print(f"::warning:: {p} is {n} lines (target {WARN})")
    return bad


if __name__ == "__main__":
    bad = offenders()
    for path, n in bad:
        print(f"LOC VIOLATION  {path}: {n} lines (max {HARD}) — split this file")
    sys.exit(1 if bad else 0)
