"""The worked designs, in the order the chapter walks them.

register() adds a spec (a dict or a TOML path) so a later chapter can
grow the set without editing this file; Chapter 45 adds its internal
designs this way. Files in data/ that start with an underscore are
exercises, not designs, and are never registered.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

ORDER = ("telecom-care", "lakeshore-rebooking", "lakeshore-refunds",
         "bank-payments", "insurer-claims", "lender-collections")

DESIGNS: dict[str, dict] = {}


def load_spec(path: str | Path) -> dict:
    p = Path(path)
    if not p.suffix:
        p = DATA / f"{p}.toml"
    return tomllib.loads(p.read_text())


def register(spec: dict | str | Path) -> str:
    """Add a design; return its id. A later spec replaces an earlier."""
    if not isinstance(spec, dict):
        spec = load_spec(spec)
    did = spec["design"]["id"]
    DESIGNS[did] = spec
    return did


def get(did: str) -> dict:
    return DESIGNS[did]


def _load_shipped() -> None:
    for did in ORDER:
        if (DATA / f"{did}.toml").exists():
            register(DATA / f"{did}.toml")
    for p in sorted(DATA.glob("*.toml")):
        if not p.name.startswith("_") and p.stem not in DESIGNS:
            register(p)


_load_shipped()
