"""Chapter 40 demo: from a project's control plane to a platform.

    python3 -m agentplatform.demo                    # every part
    python3 -m agentplatform.demo --part project     # August 10
    python3 -m agentplatform.demo --part template [--as-built]
    python3 -m agentplatform.demo --part extract     # August 14
    python3 -m agentplatform.demo --part onboard     # loyalty
    python3 -m agentplatform.demo --part conformance [--bypass]
    python3 -m agentplatform.demo --part chain
    python3 -m agentplatform.demo --part onboarding  # 31 and 9 days
    python3 -m agentplatform.demo --part economics [--charge]
    python3 -m agentplatform.demo --part card        # August 31

Offline, deterministic, Chicago clock (CDT). No model call and no
key. The records are synthetic; Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse

from common.text import emit
from gateway.servers import loyalty_server
from policy.engine import Request
from gateway.core import Caller
from policy.world import DESK, build as build_june

from . import (card, chain, conformance, economics, onboard,
               onboarding, plane, template)


def part_project(a) -> None:
    emit("== the project's control plane, Monday, August 10 ==")
    w = build_june(start="2026-08-10T14:00:00-05:00")
    gw = w.gateway
    w.servers["loyalty-points"] = loyalty_server()
    desk = template.load("desk")        # narrowed July 23, in code
    gw.callers[DESK] = Caller("desk:assistant",
                              frozenset(t["name"] for t in desk["tools"]))
    emit(f"callers, defined in code: {len(gw.callers)}")
    for key, c in gw.callers.items():
        emit(f"  {key:22} {c.sub:22} {len(c.tools):2} tools")
    r = gw.call("wl-loyalty-agent", "loyalty-points", "points_credit",
                {"member_id": "MBR-30000417", "points": 2500})
    emit(f"loyalty token:      {r.reason}")
    r = gw.call("wl-servicing-agent", "loyalty-points",
                "points_balance", {"customer_id": "C-417"})
    emit(f"loyalty tool:       {r.reason}")
    d = w.engine.decide(Request("agent:loyalty", "points_credit",
                                "effect", {"points": 2500}, "s-1"))
    emit(f"loyalty rule:       {d.verdict}, {d.reason}")
    rules = w.bundles.active().rules
    tools = sorted({t for r in rules for t in r.get("tools", [])})
    emit(f"bundle {w.bundles.active().revision}: {len(rules)} rules "
         f"on {len(tools)} tools, all servicing's")
    emit("run token binds:    itinerary (one trip)")
    emit("golden sets:        1 (servicing)")
    emit("the demo's path:    own proxy, own keys, limit in prompt")


def part_template(a) -> None:
    if a.as_built:
        emit("== loyalty as built, August 10, against the template ==")
        probs = template.check(template.as_built_aug10())
    else:
        emit("== loyalty manifest, August 17, against the template ==")
        p = plane.build()
        m = onboard.with_kinds(p, template.load("loyalty"))
        probs = template.check(m, p.world.bundles.active().rules)
    for x in probs:
        emit(f"  {x}")
    emit(f"problems: {len(probs)}")


def show(ob) -> None:
    emit(f"-- {ob.use_case}")
    for step, ok, detail in ob.steps:
        emit(f"  {step:12} {'ok  ' if ok else 'FAIL'} {detail}")
    emit(f"  live: {'yes' if ob.live else 'no'}")


def part_extract(a) -> None:
    emit("== extraction, Friday, August 14: callers from manifests ==")
    p = plane.build()
    emit(f"hard-wired callers retired; left: {sorted(p.gateway.callers)}")
    for ob in onboard.extract(p):
        show(ob)
    emit(f"callers now: {len(p.gateway.callers) - 1} from manifests, "
         f"1 loop (fare watch)")


def part_onboard(a) -> None:
    emit("== loyalty on the golden path, August 17 to 26 ==")
    p = plane.build()
    onboard.extract(p)
    ob = onboard.onboard(p, template.load("loyalty"), "pb-2026.08.24")
    show(ob)
    b = p.world.bundles.active()
    emit(f"bundle {b.revision}: {len(b.rules)} rules, signed by "
         f"{plane.SIGNER}")


def part_conformance(a) -> None:
    label = "old ledger key still valid" if a.bypass else "clean"
    emit(f"== conformance, loyalty ({label}) ==")
    p = plane.build()
    onboard.extract(p)
    ob = onboard.onboard(p, template.load("loyalty"), "pb-2026.08.24",
                         bypass=1 if a.bypass else 0)
    for c in ob.checks:
        emit(f"  {c.id} {c.name:10} {'pass' if c.ok else 'FAIL'}  "
             f"{c.detail}")
    emit(f"passed {conformance.passed(ob.checks)} of 6; live: "
         f"{'yes' if ob.live else 'no'}")
    if a.bypass:
        _, n, _ = chain.coverage(p, p.manifests["loyalty"])
        srv = p.world.servers["loyalty-points"]
        fwd = srv.requests - p.reconcile()["unmatched"][srv.name]
        emit(f"loyalty-points: gateway forwarded {fwd}, server "
             f"answered {srv.requests}")
        emit(f"chain coverage reads the trail: it counts {n} effects")


def part_chain(a) -> None:
    emit("== evidence-chain links, one effect per use case ==")
    p, obs = card.august()
    heads = ("decide",) + chain.LINKS[1:]
    cols = " ".join(f"{k:7}" for k in heads)
    emit(f"  {'':9} {'':15} {cols}".rstrip())
    for name in template.USE_CASES:
        m = p.manifests[name]
        e = chain.effects(p, m)[0]
        marks = " ".join(f"{'yes' if e.links[k] else 'NO':7}"
                         for k in chain.LINKS)
        emit(f"  {name:9} {e.tool:15} {marks}".rstrip())
    emit("coverage, August sample:")
    for name in template.USE_CASES:
        full, n, miss = chain.coverage(p, p.manifests[name])
        tail = f"  missing {', '.join(miss)}" if miss else ""
        emit(f"  {name:9} {full:3} of {n:3} effects{tail}")
    v = p.manifests["loyalty"]["verify"]
    emit(f"loyalty verifier reads through: {v['reads_through']}")


def part_onboarding(a) -> None:
    for title, st in (("desk, by meeting", onboarding.DESK),
                      ("loyalty, paved road", onboarding.LOYALTY)):
        n = onboarding.meetings(st)
        emit(f"== {title}: {onboarding.total(st)} days, "
             f"{n} meeting{'' if n == 1 else 's'} ==")
        for s in st:
            emit(f"  {s.name:22} {s.start:%b %d}-{s.end:%b %d} "
                 f"{s.days:3} d  {s.meetings} mtg")


def part_economics(a) -> None:
    if a.charge:
        emit("== charging three use cases, August (USD a month) ==")
        emit(f"  {'use case':10} {'by calls':>9} {'equal':>8} "
             f"{'marginal':>9} {'own':>8}")
        for k, calls, eq, marg, own in economics.charges():
            emit(f"  {k:10} {calls:9,.0f} {eq:8,.0f} {marg:9,.0f} "
                 f"{own:8,.0f}")
        emit("by calls, servicing pays more than its own plane")
        emit("equal split, loyalty saves about 2,200 a month")
        return
    emit("== one control plane or one per use case (USD a month) ==")
    for n in (1, 2, 3, 5, 10):
        word = "use cases" if n > 1 else "use case "
        emit(f"  {n:2} {word}  duplicated "
             f"{economics.duplicated(n):9,.0f}  shared "
             f"{economics.shared(n):8,.0f}")
    emit(f"break-even: {economics.break_even():.1f} use cases")
    emit(f"plus {economics.DUP_BUILD:,} to build each duplicate once")


def part_card(a) -> None:
    p, obs = card.august()
    for line in card.lines(card.compute(p, obs)):
        emit(line)


PARTS = {"project": part_project, "template": part_template,
         "extract": part_extract, "onboard": part_onboard,
         "conformance": part_conformance, "chain": part_chain,
         "onboarding": part_onboarding, "economics": part_economics,
         "card": part_card}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS))
    ap.add_argument("--as-built", action="store_true")
    ap.add_argument("--bypass", action="store_true")
    ap.add_argument("--charge", action="store_true")
    a = ap.parse_args(argv)
    for name, fn in PARTS.items():
        if a.part in (None, name):
            fn(a)
            if a.part is None:
                emit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
