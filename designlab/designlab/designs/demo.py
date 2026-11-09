"""Chapter 43 demo: six worked designs, linted by the book's own method.

    python3 -m designs.demo                       # every part
    python3 -m designs.demo --part method
    python3 -m designs.demo --part design --id bank-payments
    python3 -m designs.demo --part lint
    python3 -m designs.demo --part lint --fault actor-verifies
    python3 -m designs.demo --part lint --fault no-gate
    python3 -m designs.demo --part lint --set bank-payments:transfer.limit_usd=2500
    python3 -m designs.demo --part lint --add designs/data/_seventh.toml
    python3 -m designs.demo --part states --id lakeshore-refunds
    python3 -m designs.demo --part patterns
    python3 -m designs.demo --part cost
    python3 -m designs.demo --part card

Offline and deterministic. No model call and no key. Every
organization but Lakeshore is an illustrative composite; Lakeshore
figures are illustrative.
"""
from __future__ import annotations

import argparse
import copy
import sys

from common.text import emit
from method.design import from_dict

from . import registry
from .economics import month
from .lint import RULES, gap_status, lint, method_lint
from .patterns import SHORT, table
from .templates import (STATE_KEYS, STATES, TIER_WORDS, derived_tier,
                        expand)

PARTS = ("method", "design", "lint", "states", "patterns", "cost",
         "card")
STEPS = (("frame the effect", "scope, effects, tiers, owner"),
         ("estimate", "worst hour, gate items, people"),
         ("draw the chain", "diagram in the grammar"),
         ("close five gaps", "G1 to G5, each with an owner"),
         ("cost it", "seven lines per verified outcome"),
         ("record the decision", "what reverses it"))


def _money(v: float) -> str:
    return f"${v:,.2f}" if v < 100 else f"${v:,.0f}"


def _fit(line: str) -> str:
    """Trim to 70 characters at a word boundary."""
    if len(line) <= 70:
        return line
    return line[:70].rsplit(" ", 1)[0]


def _show(f) -> None:
    """One finding; the message on its own line when it is long."""
    line = f"  {f.line()}"
    if len(line) <= 70:
        emit(line)
        return
    emit(f"  {f.rule:<6} {f.where}"[:70])
    words, cur = f.message.split(), "         "
    for w in words:
        if len(cur) + len(w) + 1 > 70:
            emit(cur.rstrip())
            cur = "         "
        cur += w + " "
    emit(cur.rstrip())


def _apply_set(specs: dict, expr: str) -> tuple[str, str]:
    """ID:EFFECT.FIELD=VALUE; returns (design id, effect name)."""
    target, _, value = expr.partition("=")
    did, _, path = target.partition(":")
    name, _, field = path.partition(".")
    for e in specs[did]["effects"]:
        if e["name"] == name:
            e[field] = float(value) if field == "limit_usd" else value
    return did, name


def _fault(specs: dict, fault: str, did: str | None) -> str:
    if fault == "actor-verifies":
        did = did or "lakeshore-refunds"
        s = specs[did]
        v = s["verifiers"][0]
        v["reads"] = s["executor"]["writes"][0]
        v.pop("written_by", None)
        return did
    if fault == "no-gate":
        did = did or "lender-collections"
        specs[did].pop("human_gate", None)
        for e in specs[did]["effects"]:
            if e.get("reserved") and e["tier"] == "suggest":
                e["tier"] = "notify"
        return did
    raise SystemExit(f"unknown fault {fault}")


def part_method(a, specs) -> None:
    emit("== the method, applied six times ==")
    for i, (step, what) in enumerate(STEPS, 1):
        emit(f"{i} {step:<20} {what}")
    emit("")
    emit(f"{'design':<20}{'effects':>8}{'verif':>6}{'gate/h':>8}"
         f"{'people':>8}")
    for did, s in specs.items():
        d = from_dict(expand(s))
        emit(f"{did:<20}{len(s['effects']):>8}"
             f"{len(s['verifiers']):>6}"
             f"{d.values['gate_items_per_hour']:>8,.0f}"
             f"{d.values['reviewers_needed']:>8.1f}")


def part_design(a, specs) -> None:
    s = specs[a.id or "telecom-care"]
    m = s["design"]
    emit(f"== {m['id']} {m['version']} ({m['as_of']}) ==")
    emit(f"{m['org']}"[:70])
    emit(f"owner {m['owner']}; customer {m['customer']}"[:70])
    emit(f"{'effect':<20}{'limit':>8}  {'design':<9}{'limit allows':<12}")
    for e in s["effects"]:
        lim = f"${e['limit_usd']:,.0f}" if e.get("limit_usd") else "-"
        emit(f"{e['name']:<20}{lim:>8}  {e['tier']:<9}"
             f"{derived_tier(e) or '-'}")
    for v in s["verifiers"]:
        emit(f"verifier {v['id']} reads {v['reads']}"[:70])
    g = s.get("human_gate", {})
    if g:
        emit(f"person gate: {g['label']}, {g['promise_minutes']} "
             f"minutes promised"[:70])
    d = from_dict(expand(s))
    for n in ("peak_per_hour", "gate_items_per_hour", "reviewers_needed"):
        emit(f"  {n:<22}{d.values[n]:>10,.1f}")


def _lint_rows(specs) -> tuple[int, int, int]:
    emit(f"{'design':<20}{'find':>5}{'G1-G5':>8}{'method':>8}"
         f"{'worked':>8}")
    total_g = total_f = recs = 0
    for did, s in specs.items():
        found = lint(s)
        gs = gap_status(s, found)
        rows = method_lint.checklist(found)
        ok_m = sum(1 for r in rows if r[3])
        bad = {f.rule for f in found}
        ok_w = sum(1 for n, _ in RULES if n not in bad)
        g = "".join("+" if gs[k] else "x" for k in sorted(gs))
        emit(f"{did:<20}{len(found):>5}{g:>8}{ok_m:>5}/12"
             f"{ok_w:>6}/{len(RULES)}")
        total_g += sum(gs.values())
        total_f += len(found)
        recs += len(s.get("record", {}) and [s["record"]])
    return total_f, total_g, recs


def part_lint(a, specs) -> int:
    changed = None
    if a.add:
        changed = registry.load_spec(a.add)["design"]["id"]
        specs[changed] = registry.load_spec(a.add)
        emit(f"== add {changed}, a seventh industry ==")
    if a.set:
        changed, eff = _apply_set(specs, a.set)
        e = next(x for x in specs[changed]["effects"]
                 if x["name"] == eff)
        emit(f"== set {a.set} ==")
        emit(f"{eff}: limit ${e['limit_usd']:,.0f}; the limit allows "
             f"{derived_tier(e)}; design says {e['tier']}")
    if a.fault:
        changed = _fault(specs, a.fault, a.id)
        emit(f"== fault {a.fault} on {changed} ==")
    if not changed:
        emit("== lint: six worked designs ==")
    f, g, r = _lint_rows(specs)
    if changed:
        found = lint(specs[changed])
        if len(found) <= 12:
            for x in found:
                _show(x)
        else:
            by: dict[str, list] = {}
            for x in found:
                by.setdefault(x.rule, []).append(x)
            for rule, xs in by.items():
                emit(_fit(f"  {rule:<6} x{len(xs):<3} {xs[0].where}: "
                          f"{xs[0].message}"))
    emit(f"designs {len(specs)}, records {r}, gaps closed {g} of "
         f"{5 * len(specs)}, findings {f}")
    return 1 if f else 0


def part_states(a, specs) -> None:
    s = specs[a.id or "lakeshore-refunds"]
    emit(f"== what the {s['design']['customer']} sees: "
         f"{s['design']['id']} ==")
    for k, label in zip(STATE_KEYS, STATES):
        src = s["customer"][k]
        if src == "verifier":
            src = "the effect's verifier, never the agent"
        emit(f"{label:<22}{src}"[:70])
        if k == "done":
            for v in s["verifiers"]:
                emit(f"{'':<24}{v['id']}"[:70])
    g = s["human_gate"]
    emit(f"hand-off: {g['label']}, {g['promise_minutes']} minutes"
         + (f", first {g['sync_seconds']} s live"
            if g.get("sync_seconds") else ""))
    if g.get("order"):
        emit(f"queue ordered by {g['order']}")
    emit("case summary: " + ", ".join(g["summary"]))
    emit("never shown as verification: model confidence")


def part_patterns(a, specs) -> None:
    heads = "".join(f"{SHORT.get(d, d[:3]):>5}" for d in specs)
    emit(f"{'pattern':<38}{heads}")
    for name, row in table(specs):
        cells = "".join(f"{'x' if ok else '.':>5}" for ok in row)
        emit(f"{name:<38}{cells}")


def part_cost(a, specs) -> None:
    emit(f"{'design':<20}{'agent':>8}{'person':>9}{'payback':>9}")
    for did, s in specs.items():
        m = month(s)
        emit(f"{did:<20}{_money(m.per_outcome):>8}"
             f"{_money(m.person_cost):>9}{m.payback_months:>7.1f} mo")
    s = specs["lakeshore-refunds"]
    m = month(s)
    emit("lakeshore-refunds, seven lines a month:")
    for k, v in m.lines.items():
        emit(f"  {k:<18}{_money(v):>10}")


def part_card(a, specs) -> None:
    f, g, r = 0, 0, 0
    for s in specs.values():
        found = lint(s)
        f += len(found)
        g += sum(gap_status(s, found).values())
        r += 1 if s.get("record") else 0
    emit("== worked card, November 2, 2026 ==")
    emit(f"architectures       {len(specs)}")
    emit(f"industries          "
         f"{len({s['design']['industry'] for s in specs.values()})}")
    emit(f"decision records    {r}")
    emit(f"gaps closed         {g} of {5 * len(specs)}")
    emit(f"findings            {f}")
    emit(f"worked rules        {len(RULES)}")
    emit("linted by           designs.lint: method.lint + 8 rules")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="designs.demo")
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--id")
    ap.add_argument("--fault", choices=("actor-verifies", "no-gate"))
    ap.add_argument("--set", metavar="ID:EFFECT.FIELD=VALUE")
    ap.add_argument("--add", metavar="PATH")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    specs = copy.deepcopy(registry.DESIGNS)
    parts = [a.part] if a.part else list(PARTS)
    rc = 0
    for i, p in enumerate(parts):
        if i:
            emit("")
        out = globals()[f"part_{p}"](a, specs)
        rc = rc or (out or 0)
    return rc if a.part else 0


if __name__ == "__main__":
    raise SystemExit(main())
