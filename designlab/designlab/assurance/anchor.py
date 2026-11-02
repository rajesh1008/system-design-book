"""Anchoring: a daily Merkle root of the trail, held outside engineering.

The hash chain (Chapter 32) shows that no line was edited or removed
after the next one was written. It does not stop someone who controls
the store from rewriting the whole chain from the edited line onward.
An anchor does: each day's lines are hashed into one root, and the root
is handed to a party engineering cannot write to (here, Rachel Morgan's
audit team). A sampled line is then proven by an inclusion proof, a
handful of hashes that lead from the line to that day's root.
"""
from __future__ import annotations

import hashlib
import json

from common.trail import line_hash


def _h(a: str, b: str) -> str:
    return hashlib.sha256((a + b).encode()).hexdigest()


def _levels(leaves: list[str]) -> list[list[str]]:
    levels = [list(leaves)]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        if len(cur) % 2:
            cur = cur + [cur[-1]]
        levels.append([_h(cur[i], cur[i + 1])
                       for i in range(0, len(cur), 2)])
    return levels


def root(leaves: list[str]) -> str:
    return _levels(leaves)[-1][0]


def proof(leaves: list[str], index: int) -> list[tuple[str, str]]:
    """Sibling hashes from the leaf up, each marked left or right."""
    out = []
    for level in _levels(leaves)[:-1]:
        cur = level + [level[-1]] if len(level) % 2 else level
        sib = index ^ 1
        out.append(("L" if sib < index else "R", cur[sib]))
        index //= 2
    return out


def verify(leaf: str, path: list[tuple[str, str]], expected: str) -> bool:
    h = leaf
    for side, sib in path:
        h = _h(sib, h) if side == "L" else _h(h, sib)
    return h == expected


def by_day(lines: list[str]) -> dict[str, list[int]]:
    """Line indexes grouped by the CDT date in their timestamp."""
    days: dict[str, list[int]] = {}
    for n, line in enumerate(lines):
        day = json.loads(line)["at"][:10]
        days.setdefault(day, []).append(n)
    return days


def anchors(lines: list[str]) -> dict[str, str]:
    """One root per day: what the audit team holds."""
    return {day: root([line_hash(lines[n]) for n in idx])
            for day, idx in by_day(lines).items()}


def prove(lines: list[str], n: int,
          days: dict[str, list[int]] | None = None) -> dict:
    days = days or by_day(lines)
    day = json.loads(lines[n])["at"][:10]
    idx = days[day]
    leaves = [line_hash(lines[k]) for k in idx]
    return {"day": day, "leaf": leaves[idx.index(n)],
            "path": proof(leaves, idx.index(n))}


def check(lines: list[str], held: dict[str, str]) -> list[str]:
    """Days whose recomputed root differs from the held one."""
    now = anchors(lines)
    bad = [d for d in held if now.get(d) != held[d]]
    bad += [f"{d} (not anchored)" for d in now if d not in held]
    return sorted(bad)


def rewrite(lines: list[str], n: int, key: str, value) -> list[str]:
    """What someone who controls the store can do: edit line n and
    recompute every link after it, so the chain checks clean again."""
    out = list(lines[:n])
    for k in range(n, len(lines)):
        e = json.loads(lines[k])
        if k == n:
            e[key] = value
        e["prev"] = line_hash(out[-1]) if out else "genesis"
        out.append(json.dumps(e, sort_keys=True))
    return out
