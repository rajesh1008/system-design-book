"""Demo output fits the book's code width: 70 characters per line."""
from __future__ import annotations

MAX_LINE = 70


def emit(line: str = "") -> None:
    if len(line) > MAX_LINE:
        raise ValueError(f"demo line of {len(line)} chars: {line[:40]}...")
    print(line)


def too_long(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if len(ln) > MAX_LINE]
