"""The Harness Manifest: load, resolve, hash and diff.

A manifest file names tools by name and version. Resolving it pulls in
each tool's kind and the description the model reads, so a reworded
description changes the hash even when no file in `manifests/` does.
The hash is SHA-256 over canonical JSON of the resolved manifest; the
first twelve hex digits go into every trail line.
"""
from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from pathlib import Path

from .tools import catalog

MANIFEST_DIR = Path(__file__).parent / "manifests"
SECTIONS = ("loop", "tools", "context", "stops", "budgets")


class ManifestError(ValueError):
    pass


def load(name: str) -> dict:
    path = MANIFEST_DIR / f"{name}.toml"
    with path.open("rb") as f:
        return tomllib.load(f)


def resolve(raw: dict, tools: dict | None = None) -> dict:
    """The manifest as the harness runs it, every section present."""
    tools = catalog() if tools is None else tools
    missing = [s for s in SECTIONS if s not in raw]
    if missing:
        raise ManifestError(f"manifest lacks {', '.join(missing)}")
    out = copy.deepcopy(raw)
    resolved = []
    for t in raw["tools"]:
        entry = tools.get(t["name"])
        if entry is None:
            raise ManifestError(f"unknown tool {t['name']}")
        if entry["version"] != t["version"]:
            raise ManifestError(f"{t['name']} is {entry['version']}, "
                                f"manifest says {t['version']}")
        resolved.append(dict(name=t["name"], **entry))
    out["tools"] = resolved
    return out


def canonical(m: dict) -> str:
    return json.dumps(m, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True)


def manifest_hash(m: dict) -> str:
    return hashlib.sha256(canonical(m).encode()).hexdigest()


def short(h: str) -> str:
    return h[:12]


def get(m: dict, dotted: str):
    cur = m
    for part in dotted.split("."):
        cur = cur[part]
    return cur


def apply_overrides(m: dict, overrides: dict) -> dict:
    """What actually runs when a settings file outside the repo sets
    keys: the effective harness, which is what must be hashed."""
    out = copy.deepcopy(m)
    for dotted, value in overrides.items():
        *path, last = dotted.split(".")
        cur = out
        for part in path:
            cur = cur[part]
        cur[last] = value
    return out


def diff(a, b, prefix: str = "") -> list[str]:
    """Dotted paths whose values differ between two manifests."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            p = f"{prefix}.{k}" if prefix else k
            if k not in a or k not in b:
                out.append(p)
            else:
                out += diff(a[k], b[k], p)
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            key = x.get("name", x.get("id", i)) if isinstance(x, dict) \
                else i
            out += diff(x, y, f"{prefix}[{key}]")
        return out
    return [] if a == b else [prefix]


def counts(m: dict) -> dict:
    return {"tools": len(m["tools"]), "stops": len(m["stops"]),
            "effect_tools": sum(t["kind"] == "effect" for t in m["tools"])}
