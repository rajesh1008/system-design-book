"""The trail: append-only JSON lines, each carrying the hash of the last.

`TrailWriter` writes it (in memory, or also to a file); `check_trail`
re-derives every link and reports the first line that does not follow.
Entries are redacted before they are written.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .clock import Clock, SystemClock
from .redact import redact

GENESIS = "genesis"


def line_hash(line: str) -> str:
    return hashlib.sha256(line.encode()).hexdigest()


class TrailWriter:
    def __init__(self, path: Path | None = None, clock: Clock | None = None):
        self.path = path
        self.clock = clock or SystemClock()
        self.lines: list[str] = []
        if path is not None and path.exists():
            self.lines = path.read_text().splitlines()

    def append(self, entry: dict) -> str:
        prev = line_hash(self.lines[-1]) if self.lines else GENESIS
        body = dict(redact(entry), seq=len(self.lines) + 1,
                    at=self.clock.now().isoformat(), prev=prev)
        line = json.dumps(body, sort_keys=True)
        self.lines.append(line)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(line + "\n")
        return line


def check_trail(lines: list[str]) -> list[str]:
    """Empty when every line links to the one before it."""
    problems = []
    prev = GENESIS
    for n, line in enumerate(lines, 1):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"line {n}: not JSON")
            break
        if entry.get("prev") != prev:
            problems.append(f"line {n}: link broken (edited or removed "
                            f"line before it)")
            break
        if entry.get("seq") != n:
            problems.append(f"line {n}: sequence {entry.get('seq')}")
            break
        prev = line_hash(line)
    return problems
