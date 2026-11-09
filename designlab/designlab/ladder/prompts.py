"""The twelve prompts as data, and register() to add a thirteenth."""
from __future__ import annotations

import tomllib
from pathlib import Path

from .levels import BY_CODE, LEVELS

DATA = Path(__file__).resolve().parent / "data"

PROMPTS: dict[str, dict] = {}


def register(prompt: dict) -> str:
    """Add a prompt; return its id. Refuse one that cannot be scored."""
    missing = [k for k in ("id", "level", "title", "text", "must",
                           "follow_ups") if not prompt.get(k)]
    if missing:
        raise ValueError(f"prompt lacks {', '.join(missing)}")
    if prompt["level"] not in BY_CODE:
        raise ValueError(f"unknown level {prompt['level']}")
    if len(prompt["follow_ups"]) < 2:
        raise ValueError("write at least two follow-ups in advance")
    PROMPTS[prompt["id"]] = dict(prompt)
    return prompt["id"]


def unregister(pid: str) -> None:
    PROMPTS.pop(pid, None)


def by_level() -> dict[str, list[str]]:
    out = {lv.code: [] for lv in LEVELS}
    for pid, p in PROMPTS.items():
        out[p["level"]].append(pid)
    return out


def _load() -> None:
    raw = tomllib.loads((DATA / "prompts.toml").read_text())
    for p in raw["prompt"]:
        register(p)


_load()
