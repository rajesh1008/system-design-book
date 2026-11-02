"""Load the boundary contracts and check that each one is enforced.

A contract is enforced when the test it names exists in this package's
tests. Plane names must be the four planes (or "everyone" as a reader).
"""
from __future__ import annotations

import ast
import tomllib
from pathlib import Path

HERE = Path(__file__).parent
PLANES = ("action", "control", "knowledge", "trail")


def load_contracts(path: Path | None = None) -> dict[str, dict]:
    return tomllib.loads((path or HERE / "contracts.toml").read_text())


def _test_names() -> set[str]:
    names = set()
    for f in HERE.glob("test_*.py"):
        tree = ast.parse(f.read_text())
        names |= {n.name for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef)}
    return names


def check_contracts(contracts: dict[str, dict]) -> list[str]:
    problems, tests = [], _test_names()
    ends = PLANES + ("gateway", "everyone")
    for cid, c in sorted(contracts.items()):
        for side in ("from", "to"):
            if c.get(side) not in ends:
                problems.append(f"{cid}: {side} {c.get(side)!r}")
        for field in ("carries", "guarantees", "on_violation"):
            if not c.get(field):
                problems.append(f"{cid}: no {field}")
        if c.get("test") not in tests:
            problems.append(f"{cid}: no test enforces it")
    return problems
