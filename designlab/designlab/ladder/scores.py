"""The two people's scores on the 24 calibration answers."""
from __future__ import annotations

import tomllib
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "scores.toml"


def load() -> dict:
    return tomllib.loads(DATA.read_text())


def scorer(name: str) -> dict[str, list[int]]:
    raw = load()
    return {k: v[name] for k, v in raw.items() if isinstance(v, dict)}


def sessions() -> dict[str, str]:
    raw = load()
    return {k: v["session"] for k, v in raw.items() if isinstance(v, dict)}


def split() -> tuple[list[str], list[str]]:
    """Answers scored before and after the calibration meeting."""
    cut = load()["calibrated"]
    s = sessions()
    return (sorted(a for a, d in s.items() if d < cut),
            sorted(a for a, d in s.items() if d > cut))
