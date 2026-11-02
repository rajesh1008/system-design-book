"""Chapter 33 demo: the injection and poisoning battery.

    python3 -m threats.demo --part battery
    python3 -m threats.demo --part stops
    python3 -m threats.demo --part proposals
    python3 -m threats.demo --part trace --attack T01
    python3 -m threats.demo --part trifecta
    python3 -m threats.demo --part battery --no-session
    python3 -m threats.demo --part battery --allow-host paste.example:443
    python3 -m threats.demo --part trace --attack M03 --memory-authority
"""
from __future__ import annotations

import argparse
from collections import Counter

from common.text import emit

from .battery import (CLASSES, STAGES, Lab, Options, load, run_battery,
                      run_controls, tally)
from .trifecta import legs, rule_of_two, state_change, verdict

HEAD = {"entry": "entry", "context": "ctx", "refused": "refused",
        "proposal": "propose", "effect": "effect"}


def part_battery(opts: Options) -> None:
    spec = load()
    out = run_battery(opts)
    emit(f"battery {spec['version']}, owner {spec['owner']}, "
         f"session {spec['session']}")
    emit(f"model: obeys any instruction in its context (worst case)")
    emit()
    emit(f"{'class':14}{'n':>3}" + "".join(f"{HEAD[s]:>9}"
                                         for s in STAGES))
    t = tally(out)
    for c in CLASSES:
        n = sum(t[c].values())
        emit(f"{c:14}{n:>3}" + "".join(f"{t[c][s]:>9}" for s in STAGES))
    tot = Counter(o.stage for o in out)
    emit(f"{'total':14}{len(out):>3}" + "".join(f"{tot[s]:>9}"
                                              for s in STAGES))
    ok = sum(1 for _, good in run_controls(opts) if good)
    emit()
    emit(f"controls (legitimate work): {ok} of 4 still work")
    if tot["effect"]:
        emit("effects:")
        for o in out:
            if o.stage == "effect":
                emit(f"  {o.id} {o.title[:26]:26} {o.control[:36]}")


def family(control: str) -> str:
    head = control.split(":")[0]
    if head == "gateway":
        return control
    if head.startswith("input contract"):
        return "input contract (edge)"
    return head


def part_stops(opts: Options) -> None:
    out = run_battery(opts)
    c = Counter(family(o.control) for o in out
                if o.stage in ("entry", "refused", "proposal"))
    emit(f"{'control that stopped the attack':48}{'attacks':>8}")
    for k, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])):
        emit(f"{k[:48]:48}{n:>8}")
    emit(f"{'stopped':48}{sum(c.values()):>8}")
    ctx = [o.id for o in out if o.stage == "context"]
    emit(f"read, nothing to call: {', '.join(ctx)}")


def part_proposals(opts: Options) -> None:
    out = run_battery(opts)
    for o in out:
        if o.stage == "proposal":
            tool = next(t for t, s, _ in o.calls if s == "proposal")
            emit(f"{o.id} {tool:16}{o.control}")
            emit(f"    {o.title[:62]}")


def part_trace(opts: Options, attack: str) -> None:
    a = next(x for x in load()["attack"] if x["id"] == attack)
    lab = Lab(opts)
    o = lab.run(a)
    emit(f"{a['id']} {a['title']}")
    emit(f"surface: {a['surface']}; class {a['cls']}")
    emit("context the model reads:")
    for block in lab.context:
        for line in block.splitlines()[:9]:
            for i in range(0, min(len(line), 180), 64):
                emit("  " + line[i:i + 64].rstrip())
    for tool, stage, control in o.calls:
        emit(f"model calls {tool}: {stage}")
        emit(f"  {control[:66]}")
    emit(f"furthest stage: {o.stage}")
    word = "outcome" if o.stage == "effect" else "stopped by"
    emit(f"  {word}: {o.control[:54]}")


def part_trifecta(opts: Options) -> None:
    lab = Lab(opts)
    ls = legs(lab.w.registry, lab.egress)
    for leg in ls:
        emit(f"{leg.name:17}{'yes' if leg.present else 'no':5}"
             f"{leg.evidence[:48]}")
    ch = state_change(lab.w.registry)
    emit(f"{ch.name:17}{'yes' if ch.present else 'no':5}{ch.evidence[:48]}")
    emit(f"trifecta: {verdict(ls)}")
    emit(rule_of_two(ls, ch))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="battery",
                    choices=["battery", "stops", "proposals", "trace",
                             "trifecta"])
    ap.add_argument("--attack", default="T01")
    ap.add_argument("--allow-host", action="append", default=[])
    ap.add_argument("--no-session", action="store_true")
    ap.add_argument("--memory-authority", action="store_true")
    a = ap.parse_args(argv)
    opts = Options(allow_hosts=tuple(a.allow_host),
                   session_check=not a.no_session,
                   memory_authority=a.memory_authority)
    if a.part == "trace":
        part_trace(opts, a.attack)
    else:
        {"battery": part_battery, "stops": part_stops,
         "proposals": part_proposals,
         "trifecta": part_trifecta}[a.part](opts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
