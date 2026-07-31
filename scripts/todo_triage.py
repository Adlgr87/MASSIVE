#!/usr/bin/env python3
"""Triage TODO/FIXME markers in the MASSIVE tree (optimization workflow §2.4)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "site", "node_modules", "__pycache__", ".venv", "experiments"}

PATTERN = re.compile(
    r"#\s*(TODO|FIXME|HACK|XXX|BUG)(?::\s*([\w]+))?\s*[:-]?\s*(.*)",
    re.IGNORECASE,
)


@dataclass
class TodoItem:
    file: str
    line: int
    kind: str
    description: str
    priority: str


def _priority(desc: str) -> str:
    d = desc.lower()
    if any(k in d for k in ("critical", "crash", "security", "incorrect")):
        return "CRITICAL"
    if any(k in d for k in ("memory", "performance", "reproduc", "bug")):
        return "HIGH"
    if any(k in d for k in ("refactor", "cleanup", "docs")):
        return "MEDIUM"
    return "LOW"


def collect(root: Path = ROOT) -> list[TodoItem]:
    items: list[TodoItem] = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            m = PATTERN.search(line)
            if not m:
                continue
            desc = (m.group(3) or "").strip()
            items.append(
                TodoItem(
                    file=str(path.relative_to(root)),
                    line=i,
                    kind=m.group(1).upper(),
                    description=desc,
                    priority=_priority(desc),
                )
            )
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(items, key=lambda x: (order[x.priority], x.file, x.line))


def main() -> int:
    items = collect()
    print(f"# MASSIVE TODO triage ({len(items)} items)\n")
    for p in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        bucket = [it for it in items if it.priority == p]
        if not bucket:
            continue
        print(f"## {p} ({len(bucket)})\n")
        for it in bucket:
            print(f"- `{it.file}:{it.line}` [{it.kind}] {it.description}")
        print()
    if not items:
        print("_No TODO/FIXME markers found outside experiments/site._")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
