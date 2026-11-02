"""Chapter 36 demo: python -m assurance.demo --part NAME

Parts: replay, battery, golden, bundle, anchor, pack, tamper, sample,
evidence, finding, card, live. Offline; the live part replays recorded
fixtures and reads no key. Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
import copy
import json
import time

from common.text import emit
from common.trail import check_trail
from evals import golden as G
from threats import email

from . import admissible as A
from . import anchor, bundles, case, findings, gaps, live, month
from . import pack as P
from . import scorecard

PERIOD = "2026-06"
SEED = "audit-2026-06-elena"
HOTEL = "run-0624-04676"


def _month():
    lines = month.build().lines
    return lines, anchor.anchors(lines)


def part_replay() -> None:
    for cfg in (case.JUNE_24, case.JUNE_26, case.JULY):
        r = case.replay(cfg)
        emit(f"-- {cfg['name']}")
        for s in r.steps:
            emit(f"  {s.stage:<16}{s.result}"[:70])
        emit(f"  reached: {r.reached}")


def part_battery() -> None:
    email.main([])


def part_golden() -> None:
    for name, tasks in (("gs-2026.06", G.build()),
                        ("gs-2026.07", gaps.july())):
        emit(f"-- {name}: {len(tasks)} tasks, refund_other_card "
             f"forbidden on {gaps.forbidden_on(tasks)}")
        emit(f"  {'destination source':<38}{'trust':<11}{'tasks':>6}")
        for src, trust, n in gaps.table(tasks):
            emit(f"  {src:<38}{trust:<11}{n:>6}")


def part_bundle() -> None:
    log, _ = bundles.lifecycle(41)
    for ln in log:
        emit(ln)
    log, _ = bundles.lifecycle(20)
    emit(log[-1])
    lines, _ = _month()
    seen, refused = bundles.replay_month(lines)
    emit(f"destination-v1 over June: {seen:,} proposals, "
         f"refuses {len(refused)}: {', '.join(refused)}")


def part_anchor() -> None:
    t0 = time.perf_counter()
    lines, held = _month()
    emit(f"June trail: {len(lines):,} lines, built in "
         f"{time.perf_counter() - t0:.1f} s")
    emit(f"chain problems: {len(check_trail(lines))}")
    emit(f"daily roots held by audit: {len(held)}")
    n = next(i for i, x in enumerate(lines)
             if json.loads(x).get("proposal") == "P-0624-HOTEL")
    p = anchor.prove(lines, n)
    ok = anchor.verify(p["leaf"], p["path"], held[p["day"]])
    emit(f"P-0624-HOTEL proposal is line {n + 1:,}, day {p['day']}")
    emit(f"  proof: {len(p['path'])} hashes, verifies: {ok}")
    emit(f"  root {held[p['day']][:16]}...")


def part_pack() -> None:
    t0 = time.perf_counter()
    lines, held = _month()
    pk = P.generate(lines, held, PERIOD, SEED)
    dt = time.perf_counter() - t0
    size = len(json.dumps(pk, sort_keys=True))
    emit(f"pack {PERIOD}: {size / 1024:,.0f} KB, {dt:.1f} s from "
         f"trail to seal")
    emit(f"digest {pk['digest'][:16]}..., seal {pk['seal'][:16]}...")
    a = pk["answers"]
    emit(f"P1 refunds {a['P1']['count']:,}, USD {a['P1']['amount_usd']}")
    emit(f"P2 runs {a['P2']['count']:,} across "
         f"{len(a['P2']['by'])} release windows")
    emit(f"P3 decisions under {len(a['P3']['by'])} bundles, unsigned "
         f"{len(a['P3']['exceptions'])}")
    emit(f"P4 bound to approval: exceptions "
         f"{len(a['P4']['exceptions'])}, edited {a['P4']['edited']}")
    emit(f"P5 paid elsewhere {len(a['P5']['exceptions'])}; proposed "
         f"elsewhere {', '.join(a['P5']['proposed_elsewhere'])}")
    emit(f"P6 ledger unconfirmed {len(a['P6']['exceptions'])}")
    rej = a["P7"]["rejected"][0]
    emit(f"P7 rejected {len(a['P7']['rejected'])} ({rej['why']}), "
         f"handoffs {a['P7']['handoffs']}")
    emit(f"P8 changes {a['P8']['count']}; P9 findings "
         f"{a['P9']['count']}")
    emit(f"P10 no AI notice {len(a['P10']['exceptions'])}; P11 "
         f"exceptions {len(a['P11']['exceptions'])}")
    again = P.generate(lines, held, PERIOD, SEED)
    emit(f"regenerated, same digest: {again['digest'] == pk['digest']}")
    emit(f"auditor verify: {P.verify(pk, held) or 'clean'}")


def part_tamper() -> None:
    lines, held = _month()
    n = next(i for i, x in enumerate(lines)
             if json.loads(x).get("proposal") == "P-0624-HOTEL"
             and json.loads(x)["event"] == "approval")
    e = json.loads(lines[n])
    e["verdict"] = "approved"
    edited = list(lines)
    edited[n] = json.dumps(e, sort_keys=True)
    emit("1. flip the hotel rejection to approved, no rechain")
    emit(f"   chain: {check_trail(edited)[0]}")
    re = anchor.rewrite(lines, n, "verdict", "approved")
    emit("2. same edit, every later link recomputed")
    emit(f"   chain problems: {len(check_trail(re))}")
    bad = anchor.check(re, held)
    emit(f"   anchors differ on {len(bad)} days: {bad[0]} to {bad[-1]}")
    pk = P.generate(lines, held, PERIOD, SEED)
    forged = copy.deepcopy(pk)
    forged["answers"]["P5"]["proposed_elsewhere"] = []
    emit("3. remove P-0624-HOTEL from the P5 answer in the pack")
    emit(f"   verify: {P.verify(forged, held)[0]}")
    emit("4. regenerate the pack under another seal")
    other = P.generate(lines, held, PERIOD, SEED, seal=b"not-audit")
    emit(f"   verify: {P.verify(other, held)[0]}")
    emit("5. pack built from the rechained trail")
    rp = P.generate(re, anchor.anchors(re), PERIOD, SEED)
    emit(f"   verify: {P.verify(rp, held)[0]}")


def part_sample() -> None:
    lines, held = _month()
    items = P.sample(lines, SEED, 60)
    ok = sum(1 for i in items if not P.check_sample(i, held))
    emit(f"seed {SEED!r}: 60 of 5,967 refunds")
    emit(f"complete, bound, paid form, proofs verify: {ok} of 60")
    first = items[0]
    emit(f"first: {first['run']}, {len(first['proofs'])} lines proven")
    for p in first["proofs"][:2]:
        emit(f"  {p['day']} leaf {p['leaf'][:12]}..., "
             f"{len(p['path'])} hashes")
    same = P.sample(lines, SEED, 60)
    match = [i["run"] for i in same] == [i["run"] for i in items]
    emit(f"same seed, same draw: {match}")
    other = P.sample(lines, "audit-2026-06-other", 60)
    common = len({i['run'] for i in items} & {i['run'] for i in other})
    emit(f"another seed shares {common} of 60 runs")


def part_evidence() -> None:
    for day, items in (("2026-06-24", A.JUNE_24),
                       ("2026-07-02", A.JULY_2)):
        emit(f"-- on {day}: {A.CLAIM}")
        for e in items:
            verdict, why = A.assess(e, day)
            emit(f"  {e.eid:<4}{verdict:<13}{why}"[:70])
        ok, why = A.holds(items, day, [A.REBUTTAL])
        emit(f"  holds: {ok} ({why})")


def part_finding() -> None:
    lines, held = _month()
    pk = P.generate(lines, held, PERIOD, SEED)
    f, refusals = findings.walk(P.verify(pk, held))
    for on, to, who, note in f.log:
        emit(f"{on} {to:<19}{who}")
        if note:
            emit(f"           {note}"[:70])
    for r in refusals:
        emit(r[:70])
    emit(f"state: {f.state}")


def part_card() -> None:
    lines, held = _month()
    pk = P.generate(lines, held, PERIOD, SEED)
    outs, _ = email.run_v2(email.Options36(destination=True))
    eff = sum(1 for o in outs if o.stage == "effect")
    for what, value, who in scorecard.card(pk, held, 9, eff, len(outs)):
        emit(f"{what:<30}{value:<22}{who}")


def part_live() -> None:
    live.main(["--replay"])


PARTS = {k[5:]: v for k, v in globals().items() if k.startswith("part_")}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS), required=True)
    PARTS[ap.parse_args(argv).part]()


if __name__ == "__main__":
    main()
