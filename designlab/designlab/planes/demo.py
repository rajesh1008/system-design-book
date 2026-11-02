"""Chapter 6 lab: the four planes, six contracts, the path test, and the
autonomy table, on a seeded week of January pilot work.

    python3 -m planes.demo                  # everything, seed 6
    python3 -m planes.demo --part paths     # one part
    python3 -m planes.demo --bypass         # with the injected fast path

Offline. No model is called; the loop's proposals come from the cases.
"""
from __future__ import annotations

import argparse
from collections import Counter

from common.text import emit

from .autonomy import LEVELS, check_autonomy, load_autonomy
from .contracts import check_contracts, load_contracts
from .lab import build, cases, replay
from .paths import probe_tools, unmediated_paths, wiring

PARTS = ("contracts", "autonomy", "replay", "paths", "self", "table")


def part_contracts() -> None:
    c = load_contracts()
    emit(f"contracts: {len(c)} declared")
    for cid, body in sorted(c.items()):
        emit(f"  {cid} {body['name']:<16}{body['from']:>9} -> {body['to']}")
    problems = check_contracts(c)
    emit(f"contract check: {len(problems)} problems")
    for p in problems:
        emit(f"  {p}")


def part_autonomy() -> None:
    t = load_autonomy()
    emit(f"autonomy table {t.version}")
    emit(f"  {'task':<13}{'level':<18}{'ceiling':<18}{'path'}")
    for r in t.rows.values():
        emit(f"  {r.task:<13}{r.level:<18}{r.ceiling:<18}{r.path}")
    problems = check_autonomy(t)
    emit(f"autonomy check: {len(problems)} problems")


def part_replay(seed: int, bypass: bool) -> None:
    batch = cases(seed)
    sysm = build(batch, bypass=bypass)
    s = replay(sysm, batch)
    emit(f"replay: {s['cases']} cases, seed {seed}"
         + (", fast path injected" if bypass else ""))
    per = Counter()
    for o in s["outcomes"]:
        per[(o.task, o.customer)] += 1
    emit(f"  {'task':<13}{'cases':>6}{'done':>6}{'waiting':>9}"
         f"{'person':>8}{'unconfirmed':>13}")
    for task in ("refund", "rebook", "voucher", "hotel_cancel"):
        n = sum(v for (t, _), v in per.items() if t == task)
        emit(f"  {task:<13}{n:>6}{per[(task, 'done')]:>6}"
             f"{per[(task, 'waiting for approval')]:>9}"
             f"{per[(task, 'with a person')]:>8}"
             f"{per[(task, 'in progress')]:>13}")
    p = s["path"]
    emit(f"paths: agent {p['agent']}, assisted {p['assisted']}, "
         f"person {p['person']}, unknown {p['unknown']}")
    h = s["handoff"]
    emit(f"hand-offs: sync {h['sync']} (median wait "
         f"{s['sync_p50_s']:.0f} s), async {h['async']}")
    emit(f"gateway calls {s['gateway_effects']}; effects in systems "
         f"{s['effects']}; unmediated {s['unmediated']}")
    emit(f"decision lines {s['decisions']}; trail intact {s['trail_ok']}")
    emit(f"model would have said done, not done: "
         f"{s['model_done_unverified']}")
    emit(f"customer told done without verification: "
         f"{s['told_done_unverified']}")
    if bypass:
        usd = sum(e["usd"] for e in sysm.world.unmediated())
        emit(f"unmediated refunds: {s['unmediated']}, ${usd:,.2f}, "
             f"0 permission ids, 0 trail lines")


def part_paths(seed: int, bypass: bool) -> None:
    batch = cases(seed, n=10)
    sysm = build(batch, bypass=bypass)
    edges = wiring(sysm.loop)
    found = unmediated_paths(edges)
    flagged = probe_tools(sysm.loop, sysm.world)
    emit(f"path test{' (fast path injected)' if bypass else ''}: "
         f"{len(edges)} edges")
    emit(f"  static: {len(found)} path(s) skip the gateway")
    for path in found:
        emit("    " + " -> ".join(path))
    emit(f"  probe: {len(sysm.loop.tools)} tools, "
         f"{len(flagged)} acted without a permission")
    for name in flagged:
        emit(f"    {name}")
    emit("  result: " + ("FAIL" if found or flagged else "pass"))


def part_self(seed: int) -> None:
    batch = [c for c in cases(seed) if c["task"] == "refund"][:1]
    sysm = build(batch, policy_in_loop=True)
    o = sysm.loop.run(batch[0], None)
    emit(f"policy inside the loop: {o.itinerary} ${batch[0]['usd']:,.2f}")
    emit(f"  gateway: {o.verdict}")
    emit(f"  effects in systems: {len(sysm.world.effects)}")


def part_table() -> None:
    base = load_autonomy()
    trials = {
        "refund raised to act_and_notify": ("refund", "level",
                                            "act_and_notify"),
        "voucher without a daily budget": ("voucher", "daily_budget_usd",
                                           None),
        "rebook told 'confirmed'": ("rebook", "customer_sees",
                                    ["confirmed"]),
    }
    for label, (task, field, value) in trials.items():
        t = load_autonomy()
        setattr(t.rows[task], field, value)
        problems = check_autonomy(t)
        emit(f"{label}: {len(problems)} problem(s)")
        for p in problems:
            emit(f"  {p}")
    emit("levels, lowest first:")
    emit("  " + ", ".join(LEVELS))
    emit(f"baseline table problems: {len(check_autonomy(base))}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=6)
    ap.add_argument("--part", choices=PARTS + ("all",), default="all")
    ap.add_argument("--bypass", action="store_true")
    a = ap.parse_args(argv)
    run = {
        "contracts": part_contracts, "autonomy": part_autonomy,
        "replay": lambda: part_replay(a.seed, a.bypass),
        "paths": lambda: part_paths(a.seed, a.bypass),
        "self": lambda: part_self(a.seed), "table": part_table}
    for name in (PARTS if a.part == "all" else (a.part,)):
        run[name]()


if __name__ == "__main__":
    main()
