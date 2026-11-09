"""The worked-design linter: Chapter 5's checks, then six more.

Chapter 5's linter (method.lint) reads the expanded eight artifacts.
The rules below read the spec itself, because they check what a worked
design promises a customer, a regulator, and a finance team:

    IND-1  an effect's verifier is missing, acts, or reads a record the
           executor writes
    PRM-1  an effect's tier is more autonomous than its limit allows
    HUM-1  a rule reserves a decision for a person, and the design lets
           the agent take it or has no person gate
    CUS-1  the customer states are not the six, or one has no source,
           or done does not come from a verifier
    CUS-2  a customer state comes from the model
    CUS-3  the hand-off has no promised time or the case summary a
           person receives misses a field
    REG-1  an obligation is enforced in the prompt, or nowhere
    ECO-1  the economics block is missing a line

register_rule() appends a rule; Chapter 45 adds the loop properties.
"""
from __future__ import annotations

from importlib import import_module
from typing import Callable

from method.design import from_dict
from method.lint import Finding

from .economics import INPUTS as ECO_INPUTS
from .templates import (STATE_KEYS, SUMMARY_FIELDS, derived_tier, expand,
                        rank)

method_lint = import_module("method.lint")
Rule = Callable[[dict], list[Finding]]


def ind_1(spec: dict) -> list[Finding]:
    out = []
    vers = {v["id"]: v for v in spec.get("verifiers", [])}
    writes = set(spec.get("executor", {}).get("writes", []))
    for e in spec.get("effects", []):
        if e.get("tier") in ("never", "suggest"):
            continue
        w = f"effect {e['name']}"
        v = vers.get(e.get("verifier", ""))
        if not v:
            out.append(Finding("IND-1", w, "no verifier"))
            continue
        if v.get("acts"):
            out.append(Finding("IND-1", w, f"{v['id']} acts"))
        if v.get("reads") in writes:
            out.append(Finding("IND-1", w, f"{v['id']} reads "
                               f"{v['reads']}, which the executor writes"))
    return out


def prm_1(spec: dict) -> list[Finding]:
    out = []
    for e in spec.get("effects", []):
        allowed = derived_tier(e)
        if allowed and rank(e.get("tier", "")) > rank(allowed):
            out.append(Finding(
                "PRM-1", f"effect {e['name']}",
                f"${e.get('limit_usd', 0):,.0f} allows {allowed}, "
                f"design says {e['tier']}"))
    return out


def hum_1(spec: dict) -> list[Finding]:
    out = []
    gate = spec.get("human_gate")
    for e in spec.get("effects", []):
        if not e.get("reserved"):
            continue
        w = f"effect {e['name']}"
        if rank(e.get("tier", "")) > rank("suggest"):
            out.append(Finding("HUM-1", w, f"reserved ({e['reserved']}); "
                               f"agent may {e['tier']}"))
        if not gate:
            out.append(Finding("HUM-1", w, "reserved; no person gate"))
    return out


def cus_1(spec: dict) -> list[Finding]:
    out = []
    c = spec.get("customer", {})
    for k in STATE_KEYS:
        if not c.get(k):
            out.append(Finding("CUS-1", f"state {k}", "no source"))
    done = c.get("done", "")
    ids = {v["id"] for v in spec.get("verifiers", [])}
    if done != "verifier" and done.removeprefix("verifier:") not in ids:
        out.append(Finding("CUS-1", "state done",
                           f"{done} is not a verifier"))
    return out


def cus_2(spec: dict) -> list[Finding]:
    return [Finding("CUS-2", f"state {k}", "computed from the model")
            for k, src in spec.get("customer", {}).items()
            if "model" in str(src)]


def cus_3(spec: dict) -> list[Finding]:
    out = []
    gate = spec.get("human_gate")
    if not gate:
        return out
    if not gate.get("promise_minutes"):
        out.append(Finding("CUS-3", "human_gate", "no promised time"))
    for f in SUMMARY_FIELDS:
        if f not in gate.get("summary", []):
            out.append(Finding("CUS-3", "human_gate",
                               f"summary has no {f}"))
    return out


def reg_1(spec: dict) -> list[Finding]:
    out = []
    for o in spec.get("obligations", []):
        if o.get("plane") not in ("control", "trail"):
            out.append(Finding("REG-1", f"obligation {o.get('id')}",
                               f"enforced in {o.get('plane') or 'nothing'}"))
        elif not o.get("enforced_by"):
            out.append(Finding("REG-1", f"obligation {o.get('id')}",
                               "no enforcing component"))
    return out


def eco_1(spec: dict) -> list[Finding]:
    eco = spec.get("economics", {})
    if not eco:
        return [Finding("ECO-1", "economics", "no economics block")]
    return [Finding("ECO-1", "economics", f"no {k}")
            for k in ECO_INPUTS if k not in eco]


RULES: list[tuple[str, Rule]] = [
    ("IND-1", ind_1), ("PRM-1", prm_1), ("HUM-1", hum_1),
    ("CUS-1", cus_1), ("CUS-2", cus_2), ("CUS-3", cus_3),
    ("REG-1", reg_1), ("ECO-1", eco_1),
]


def register_rule(name: str, fn: Rule) -> None:
    RULES.append((name, fn))


def lint(spec: dict) -> list[Finding]:
    """Chapter 5's findings on the expansion, then the worked rules."""
    found = list(method_lint.lint(from_dict(expand(spec))))
    for _name, fn in RULES:
        found += fn(spec)
    return found


# Which gap each worked rule speaks to.
GAP_OF = {"IND-1": "G4", "CUS-1": "G4", "CUS-2": "G4", "PRM-1": "G2",
          "HUM-1": "G2", "CUS-3": "G2", "REG-1": "G2", "ECO-1": "G5"}


def gap_status(spec: dict, found: list[Finding] | None = None
               ) -> dict[str, bool]:
    """G1 to G5: closed when answered, owned, and no finding hits it."""
    found = lint(spec) if found is None else found
    rows = {r[0]: r[3] for r in method_lint.checklist(found)}
    hit = {GAP_OF[f.rule] for f in found if f.rule in GAP_OF}
    gaps = spec.get("gaps", {})
    return {g: bool(rows.get(g) and g not in hit
                    and gaps.get(g, {}).get("answer")
                    and gaps.get(g, {}).get("owner"))
            for g in method_lint.GAPS}


def gaps_closed(spec: dict, found: list[Finding] | None = None) -> int:
    return sum(gap_status(spec, found).values())
