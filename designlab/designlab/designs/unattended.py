"""Chapter 45's rules for a design that runs with nobody asking.

A worked design with a [loop] block declares the loop in Chapter 28's
seven properties. These rules run Chapter 28's loops linter on that
block, then check that the loop agrees with the design around it:

    LOOP-1  the loop has no trigger it can be keyed on, or its state
            does not persist (gap G3: a rerun repeats or forgets)
    LOOP-2  the loop has no machine stop, budget, bounded change, or
            named person, or it takes a decision the design reserves
            for a person, or it hands off to a desk the design lacks
            (gap G2)
    LOOP-3  the loop's verifier is not one of the design's verifiers,
            or it reads what the executor writes (gap G4)

A design with no [loop] block gets no finding from these rules, so
Chapter 43's six designs lint exactly as they did.
"""
from __future__ import annotations

from loops.lint import lint as loop_lint
from method.lint import Finding

RULE_OF = {"trigger": "LOOP-1", "state": "LOOP-1", "stop": "LOOP-2",
           "budget": "LOOP-2", "change": "LOOP-2", "human": "LOOP-2",
           "verify": "LOOP-3"}


def unattended(spec: dict) -> bool:
    return "loop" in spec


def _props(spec: dict, rule: str) -> list[Finding]:
    return [Finding(rule, f"loop {f.prop}", f.why)
            for f in loop_lint(spec["loop"])
            if not f.ok and RULE_OF[f.prop] == rule]


def loop_1(spec: dict) -> list[Finding]:
    return _props(spec, "LOOP-1") if unattended(spec) else []


def loop_2(spec: dict) -> list[Finding]:
    if not unattended(spec):
        return []
    out = _props(spec, "LOOP-2")
    lp = spec["loop"]
    effects = {e["name"]: e for e in spec.get("effects", [])}
    for name in lp.get("change", {}).get("effect_tools", []):
        e = effects.get(name)
        if not e:
            out.append(Finding("LOOP-2", f"loop change {name}",
                               "not an effect of the design"))
        elif e.get("reserved"):
            out.append(Finding("LOOP-2", f"loop change {name}",
                               f"reserved ({e['reserved']})"))
        elif e.get("tier") in ("never", "suggest"):
            out.append(Finding("LOOP-2", f"loop change {name}",
                               f"design says {e['tier']}"))
    gate = spec.get("human_gate", {}).get("label")
    hand = lp.get("human", {}).get("hand_off")
    if hand and hand != gate:
        out.append(Finding("LOOP-2", "loop human",
                           f"hands off to {hand}; no such desk"))
    return out


def loop_3(spec: dict) -> list[Finding]:
    if not unattended(spec):
        return []
    out = _props(spec, "LOOP-3")
    vid = spec["loop"].get("verify", {}).get("verifier", "")
    vers = {v["id"]: v for v in spec.get("verifiers", [])}
    writes = set(spec.get("executor", {}).get("writes", []))
    if vid and vid not in vers:
        out.append(Finding("LOOP-3", "loop verify",
                           f"{vid} is not a verifier of the design"))
    for src in spec["loop"].get("verify", {}).get("reads", []):
        if src in writes:
            out.append(Finding("LOOP-3", "loop verify",
                               f"reads {src}, which the executor writes"))
    return out
