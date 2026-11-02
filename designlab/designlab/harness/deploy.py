"""The deploy check: refuse any harness that is not a registered release.

It hashes the effective harness (the manifest with every runtime
override applied), not the file in the repo, because the May 27 change
lived in a settings file the repo never saw.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .manifest import apply_overrides, manifest_hash, resolve, short

RELEASES = Path(__file__).parent / "releases.toml"


def releases(path: Path = RELEASES) -> dict[str, dict]:
    with path.open("rb") as f:
        return tomllib.load(f).get("release", {})


@dataclass
class Verdict:
    ok: bool
    version: str
    hash: str
    reason: str


def check(raw: dict, overrides: dict | None = None,
          registry: dict | None = None) -> Verdict:
    reg = releases() if registry is None else registry
    eff = apply_overrides(resolve(raw), overrides or {})
    h = manifest_hash(eff)
    v = eff.get("version", "")
    if not v:
        return Verdict(False, "", h, "no version")
    rel = reg.get(v)
    if rel is None:
        return Verdict(False, v, h, f"{v} is not registered")
    if rel.get("status") != "released":
        return Verdict(False, v, h, f"{v} is {rel.get('status')}")
    if rel["hash"] != h:
        return Verdict(False, v, h, f"hash {short(h)} is not {v} "
                                    f"({short(rel['hash'])})")
    return Verdict(True, v, h, "registered")
