"""The context assembler: slots in a fixed order, caps, a budget, and
an alarm whenever a cap or the budget is passed.

The assembler does not decide what is true. It decides what fits, in
which order, and who hears about it when something did not fit. It
renders its output as Chapter 14 serving segments and runs the serving
layout lint on them, so the order that protects quality is checked by
the same code that protects the prefix cache.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common.trail import TrailWriter
from serving.layout import Rendered, lint as layout_lint
from serving.trace import Seg

from .slots import ORDER, STABLE, Budget, Item


@dataclass
class Assembled:
    items: list[Item]
    tokens: int
    by_slot: dict
    cut: dict = field(default_factory=dict)      # slot -> tokens cut
    alarms: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)   # layout lint

    @property
    def over_budget(self) -> bool:
        return any(a.startswith("budget") for a in self.alarms)


_PREFIX = {"task": "itin", "memory": "mem", "history": "hist",
           "retrieved": "ret", "pinned": "pin", "clock": "ts"}


def to_segs(items: list[Item]) -> list[Seg]:
    """Stable items keep their release keys (tools-v4 and so on); every
    other item gets a dynamic prefix, which is what the lint keys on."""
    out = []
    for it in items:
        key = it.key if it.slot in STABLE else \
            f"{_PREFIX[it.slot]}:{it.key}"
        out.append(Seg(key, it.tokens))
    return out


def breakpoints(items: list[Item]) -> list[int]:
    """One after the stable slots, one after the history."""
    bps = []
    last_stable = max((i for i, it in enumerate(items)
                       if it.slot in STABLE), default=-1)
    if last_stable >= 0:
        bps.append(last_stable)
    last_hist = max((i for i, it in enumerate(items)
                     if it.slot == "history"), default=-1)
    if last_hist > last_stable:
        bps.append(last_hist)
    return bps


def _cap(slot: str, items: list[Item], cap: int | None):
    """Keep items by rank until the cap; history is never cut here."""
    if cap is None or slot == "history":
        return items, 0
    kept, used, cut = [], 0, 0
    for it in sorted(items, key=lambda i: i.rank):
        if used + it.tokens <= cap:
            kept.append(it)
            used += it.tokens
        else:
            cut += it.tokens
    order = {id(i): n for n, i in enumerate(items)}
    kept.sort(key=lambda i: order[id(i)])
    return kept, cut


def assemble(parts: dict[str, list[Item]], budget: Budget | None = None,
             order: tuple[str, ...] = ORDER,
             trail: TrailWriter | None = None, run: str = "",
             step: int = 0, alarms_on: bool = True) -> Assembled:
    budget = budget or Budget()
    items: list[Item] = []
    by_slot: dict[str, int] = {}
    cut: dict[str, int] = {}
    alarms: list[str] = []
    for slot in order:
        got = parts.get(slot, [])
        cap = budget.caps.get(slot)
        if slot in STABLE and cap is not None:
            size = sum(i.tokens for i in got)
            if size > cap:            # a release grew: say so, cut nothing
                alarms.append(f"cap {slot} {size:,} > {cap:,}")
            kept, n = got, 0
        else:
            kept, n = _cap(slot, got, cap)
        if n:
            cut[slot] = n
            alarms.append(f"cap {slot} cut {n:,}")
        items.extend(kept)
        by_slot[slot] = sum(i.tokens for i in kept)
    total = sum(by_slot.values())
    if total > budget.per_step:
        top = max((s for s in by_slot if s not in STABLE),
                  key=lambda s: by_slot[s])
        alarms.append(f"budget {total:,} > {budget.per_step:,} "
                      f"({top} {by_slot[top]:,})")
    if not alarms_on:
        alarms = []
    segs = to_segs(items)
    findings = layout_lint(Rendered(segs, breakpoints(items)))
    if trail is not None:
        for a in alarms:
            trail.append({"event": "context.alarm", "run": run,
                          "step": step, "alarm": a, "tokens": total})
    return Assembled(items, total, by_slot, cut, alarms, findings)


def reuse(prev: Assembled | None, cur: Assembled) -> int:
    """Tokens of `cur` that repeat `prev` from the first token: what a
    prefix cache could read instead of compute."""
    if prev is None:
        return 0
    n = 0
    for a, b in zip(prev.items, cur.items):
        if a.key != b.key or a.tokens != b.tokens or a.slot != b.slot:
            break
        if a.slot == "clock":
            break
        n += a.tokens
    return n
