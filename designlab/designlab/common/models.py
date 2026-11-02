"""Pinned model IDs, read from models.toml. Code asks for a role."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MODELS_TOML = Path(__file__).with_name("models.toml")


@dataclass(frozen=True)
class ModelPin:
    role: str
    id: str
    display: str
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    cache_read_usd_per_mtok: float


@lru_cache(maxsize=None)
def load(path: Path = MODELS_TOML) -> dict:
    with path.open("rb") as f:
        return tomllib.load(f)


def pins(path: Path = MODELS_TOML) -> dict[str, ModelPin]:
    data = load(path)
    return {role: ModelPin(role=role, id=r["id"], display=r["display"],
                           input_usd_per_mtok=r["input_usd_per_mtok"],
                           output_usd_per_mtok=r["output_usd_per_mtok"],
                           cache_read_usd_per_mtok=r[
                               "cache_read_usd_per_mtok"])
            for role, r in data["roles"].items()}


def pin(role_or_id: str) -> ModelPin:
    """Look up by role ("small") or by exact pinned ID. Unpinned IDs fail."""
    all_pins = pins()
    if role_or_id in all_pins:
        return all_pins[role_or_id]
    for p in all_pins.values():
        if p.id == role_or_id:
            return p
    raise KeyError(f"model {role_or_id!r} is not pinned in models.toml")


def api_version() -> str:
    return load()["api_version"]
