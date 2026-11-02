"""Redaction and secret scanning.

Nothing that leaves the client (a log line, a cache entry, a fixture,
a trail entry) may carry a credential. `redact` blanks credential-shaped
keys and values; `find_secrets` is what the fixture check runs.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

MASK = "[REDACTED]"
SECRET_KEYS = re.compile(
    r"(api[-_]?key|authorization|secret|password|cookie|bearer"
    r"|(access|auth|refresh|session)[-_]?token|^token$)", re.I)
# Provider key shapes. Built from parts so this file never matches itself.
KEY_SHAPES = [
    re.compile("sk" + r"-ant-[A-Za-z0-9_\-]{8,}"),
    re.compile("gh" + r"p_[A-Za-z0-9]{20,}"),
    re.compile("AK" + r"IA[0-9A-Z]{16}"),
]
# Strings a recorded fixture must never contain (designlab plan, rule 3).
FIXTURE_BANNED = ["x-api" + "-key", "sk" + "-ant"]
ENV_KEYS = ("ANTHROPIC_API_KEY",)


def _env_values() -> list[str]:
    return [v for k in ENV_KEYS if len(v := os.environ.get(k, "")) >= 8]


def redact_text(text: str) -> str:
    for shape in KEY_SHAPES:
        text = shape.sub(MASK, text)
    for value in _env_values():
        text = text.replace(value, MASK)
    return text


def redact(obj: Any) -> Any:
    """Return a copy of obj with credentials masked, at any depth."""
    if isinstance(obj, dict):
        return {k: (MASK if isinstance(k, str) and SECRET_KEYS.search(k)
                    else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return type(obj)(redact(v) for v in obj)
    if isinstance(obj, str):
        return redact_text(obj)
    return obj


def find_secrets(text: str, fixture: bool = False) -> list[str]:
    """Names of what was found; empty means clean."""
    found = [s.pattern[:12] for s in KEY_SHAPES if s.search(text)]
    found += ["environment key value" for v in _env_values() if v in text]
    if fixture:
        low = text.lower()
        found += [b for b in FIXTURE_BANNED if b in low]
    return found


def scan_tree(root: Path, fixture_dirs: tuple[str, ...] = ("fixtures",)
              ) -> dict[str, list[str]]:
    """Scan every text file under root. Files inside a fixtures directory
    also fail on the banned header and key-prefix strings."""
    problems: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        is_fixture = any(d in path.parts for d in fixture_dirs)
        hits = find_secrets(text, fixture=is_fixture)
        if hits:
            problems[str(path.relative_to(root))] = hits
    return problems
