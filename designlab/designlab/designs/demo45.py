"""Chapter 45 demo: six internal designs added to Chapter 43's six.

    python3 -m designs.demo45                     # every part
    python3 -m designs.demo45 --part method
    python3 -m designs.demo45 --part design --id lakeshore-itops
    python3 -m designs.demo45 --part lint
    python3 -m designs.demo45 --part lint --fault no-state
    python3 -m designs.demo45 --part lint --fault no-change-control
    python3 -m designs.demo45 --part lint --fault no-budget
    python3 -m designs.demo45 --part lint --fault raw-sql
    python3 -m designs.demo45 --part loops
    python3 -m designs.demo45 --part privilege
    python3 -m designs.demo45 --part patterns
    python3 -m designs.demo45 --part cost
    python3 -m designs.demo45 --part recon
    python3 -m designs.demo45 --part records
    python3 -m designs.demo45 --part card

Offline and deterministic. No model call and no key. Every
organization but Lakeshore is an illustrative composite; Lakeshore
figures are illustrative.
"""
from __future__ import annotations

import argparse
import copy
import sys
from importlib import import_module

from common.text import emit
from loops.lint import PROPS
from loops.lint import lint as loop_lint
from method.design import from_dict

from . import internal
from .demo import _fit, _show
from .economics import month
from .patterns import PATTERNS as BASE
from .patterns import SHORT as BASE_SHORT
from .privilege import requested_vs_designed
from .recon import lanes, tolerance_trial
from .records import due_by_month, store, to_record
from .templates import expand

worked = import_module("designs.lint")
PARTS = ("method", "design", "lint", "loops", "privilege", "patterns",
         "cost", "recon", "records", "card")
FAULTS = ("no-state", "no-change-control", "no-budget", "raw-sql")


def _money(v: float) -> str:
    return f"${v:,.2f}" if v < 100 else f"${v:,.0f}"


def _short(did: str) -> str:
    return internal.SHORT.get(did) or BASE_SHORT.get(did, did[:3])


def _fault(specs: dict, fault: str) -> str:
    if fault == "no-state":
        did = "lakeshore-compliance"
        specs[did]["loop"]["state"]["store"] = "process memory"
    elif fault == "no-change-control":
        did = "lakeshore-itops"
        s = specs[did]
        for e in s["effects"]:
            if e["name"] == "config_change":
                e["tier"] = "act"
        ch = s["loop"]["change"]
        ch["grant"].append("config_change")
        ch["effect_tools"].append("config_change")
        ch["effects"]["config_change"] = {"rollback_minutes": 10}
    elif fault == "no-budget":
        did = "lakeshore-research"
        specs[did]["loop"]["budget"] = {"enforced_by": "system prompt"}
    elif fault == "raw-sql":
        did = "lakeshore-analytics"
        s = specs[did]
        for o in s["obligations"]:
            if o["id"] == "certified":
                o["plane"] = "prompt"
        p = s["privilege"]
        p["standing"] = ["warehouse read on all schemas"]
        p["writes"] = ["warehouse"] + p["writes"]
    else:
        raise SystemExit(f"unknown fault {fault}")
    return did


def part_method(a, specs) -> None:
    emit("== the method, applied six times more ==")
    emit(f"{'design':<21}{'effects':>7}{'verif':>6}{'loop':>5}"
         f"{'gate/h':>8}{'people':>8}")
    for did in internal.ORDER:
        s = specs[did]
        d = from_dict(expand(s))
        emit(f"{did:<21}{len(s['effects']):>7}"
             f"{len(s['verifiers']):>6}"
             f"{'yes' if 'loop' in s else 'no':>5}"
             f"{d.values['gate_items_per_hour']:>8,.1f}"
             f"{d.values['reviewers_needed']:>8.2f}")
    emit("same six steps; two more blocks: privilege and loop")


def part_design(a, specs) -> None:
    s = specs[a.id or "lakeshore-itops"]
    m = s["design"]
    emit(f"== {m['id']} {m['version']} ({m['as_of']}) ==")
    emit(_fit(f"owner {m['owner']}; asked by the {m['customer']}"))
    emit(f"{'effect':<18}{'tier':<9}reserved for a person")
    for e in s["effects"]:
        emit(_fit(f"{e['name']:<18}{e['tier']:<9}"
                  f"{e.get('reserved', '-')}"))
    p = s["privilege"]
    emit(_fit(f"credential: {p['credential']}, "
              f"{p['ttl_minutes']} min"))
    emit(f"standing credentials: {len(p['standing'])}")
    if "loop" in s:
        lp = s["loop"]
        emit(_fit(f"loop {lp['loop']}: {', '.join(lp['trigger']['kinds'])}"
                  f", ${lp['budget']['run_usd']:.2f} a run"))


def _lint_rows(specs) -> tuple[int, int, int]:
    emit(f"{'design':<21}{'find':>5}{'G1-G5':>8}{'method':>8}"
         f"{'worked':>8}")
    tg = tf = recs = 0
    n = len(worked.RULES)
    for did, s in specs.items():
        found = worked.lint(s)
        gs = worked.gap_status(s, found)
        rows = worked.method_lint.checklist(found)
        ok_m = sum(1 for r in rows if r[3])
        bad = {f.rule for f in found}
        ok_w = sum(1 for name, _ in worked.RULES if name not in bad)
        g = "".join("+" if gs[k] else "x" for k in sorted(gs))
        emit(f"{did:<21}{len(found):>5}{g:>8}{ok_m:>5}/12"
             f"{ok_w:>5}/{n}")
        tg += sum(gs.values())
        tf += len(found)
        recs += 1 if s.get("record") else 0
    return tf, tg, recs


def part_lint(a, specs) -> int:
    changed = None
    if a.fault:
        changed = _fault(specs, a.fault)
        emit(f"== fault {a.fault} on {changed} ==")
    else:
        emit("== lint: twelve worked designs ==")
    f, g, r = _lint_rows(specs)
    if changed:
        for x in worked.lint(specs[changed]):
            _show(x)
    emit(f"designs {len(specs)}, records {r}, gaps closed {g} of "
         f"{5 * len(specs)}, findings {f}")
    return 1 if f else 0


def part_loops(a, specs) -> None:
    heads = "".join(f"{p[:5]:>7}" for p in PROPS)
    emit(f"{'loop':<17}{heads}")
    for did in internal.ORDER:
        s = specs[did]
        if "loop" not in s:
            emit(f"{s['design']['id'][10:]:<17}  no loop: a person "
                 "asks every time")
            continue
        cells = "".join(f"{'ok' if x.ok else 'FAIL':>7}"
                        for x in loop_lint(s["loop"]))
        emit(f"{s['loop']['loop']:<17}{cells}")


def part_privilege(a, specs) -> None:
    emit("== privilege: the October request against the design ==")
    emit(f"{'design':<21}{'standing':>9}{'now':>5}{'writes':>8}"
         f"{'now':>5}{'ttl':>6}")
    asked = 0
    for did in internal.ORDER:
        p = requested_vs_designed(specs[did])
        asked += p["standing_asked"]
        emit(f"{did:<21}{p['standing_asked']:>9}{p['standing_now']:>5}"
             f"{p['writes_asked']:>8}{p['writes_now']:>5}"
             f"{p['ttl']:>4} m")
    emit(f"standing credentials asked {asked}, designed 0")
    rr = next(r for r in store() if r["id"] == "RR-02")
    emit(_fit(f"RR-02 revisit {rr['revisit_date']}, trigger:"))
    emit(_fit(f"  {rr['revisit_trigger']}"))


LABELS = ("permission outside", "independent verifier",
          "status from chain", "promised hand-off",
          "obligations outside", "tier by amount", "kept for a person",
          "never by the agent", "surge rule signed",
          "no standing access", "loop, 7 properties",
          "record, other signer")


def part_patterns(a, specs) -> None:
    pats = list(zip(LABELS, [fn for _, fn in
                             list(BASE) + list(internal.PATTERNS)]))
    heads = "".join(f"{_short(d):>4}" for d in specs)
    emit(f"{'pattern':<22}{heads}")
    for name, fn in pats:
        cells = "".join(f"{'x' if fn(s) else '.':>4}"
                        for s in specs.values())
        emit(f"{name[:21]:<22}{cells}")


def part_cost(a, specs) -> None:
    emit(f"{'design':<21}{'agent':>8}{'person':>9}{'payback':>10}")
    for did in internal.ORDER:
        m = month(specs[did])
        emit(f"{did:<21}{_money(m.per_outcome):>8}"
             f"{_money(m.person_cost):>9}{m.payback_months:>7.1f} mo")
    m = month(specs["lakeshore-itops"])
    emit("lakeshore-itops, seven lines a month:")
    for k, v in m.lines.items():
        emit(f"  {k:<18}{_money(v):>10}")


def part_recon(a, specs) -> None:
    signed, wide = tolerance_trial()
    emit("== closing by tolerance: one synthetic month ==")
    emit(f"{'tolerance':<22}{'auto-match':>11}{'false':>7}"
         f"{'absorbed':>10}")
    for label, t in (("signed: $0, 1 day", signed),
                     ("widened: 0.5%, 3 days", wide)):
        emit(f"{label:<22}{t.rate:>10.2%}{t.false:>7}"
             f"{_money(t.absorbed_usd):>10}")
    emit(f"lines {signed.lines:,}")
    w = lanes()
    emit("")
    emit("== which lane decides when recovery ends ==")
    emit(f"breaks {w['breaks']}; generalist lanes done in "
         f"{w['general_hours']:.1f} h")
    emit(f"duplicate-charge lane done in {w['special_hours']:.1f} h")
    emit(f"cleared by count at {w['general_hours']:.1f} h: "
         f"{w['cleared_by_count']:.0%}")
    emit(f"value at risk left then: ${w['value_left']:,.0f} of "
         f"${w['value_total']:,.0f}")


def part_records(a, specs) -> None:
    emit("== six review records, Chapter 42's validator ==")
    emit(f"{'record':<9}{'owner':<17}{'signer':<17}{'revisit':<11}"
         f"{'ok':>3}")
    from review.record import validate
    new = []
    for did in internal.ORDER:
        r = to_record(specs[did])
        new.append({"revisit_date": r.revisit_date, "status": "active"})
        emit(f"{r.id:<9}{r.owner[:16]:<17}{r.signer[:16]:<17}"
             f"{r.revisit_date:<11}{'yes' if not validate(r) else 'no':>3}")
    before = due_by_month()
    after = due_by_month(store() + new)
    emit("revisits due by month, store before and after:")
    for mth in sorted(after):
        if mth >= "2026-11":
            emit(f"  {mth}  {before[mth]:>2}  {after[mth]:>2}")


def part_card(a, specs) -> None:
    f = g = r = loops = 0
    for s in specs.values():
        found = worked.lint(s)
        f += len(found)
        g += sum(worked.gap_status(s, found).values())
        r += 1 if s.get("record") else 0
        loops += 1 if "loop" in s else 0
    facing = sum(1 for s in specs.values()
                 if s["design"].get("facing") == "internal")
    emit("== worked card, November 2, 2026 ==")
    emit(f"architectures       {len(specs)}")
    emit(f"  customer-facing   {len(specs) - facing}")
    emit(f"  internal          {facing}")
    emit(f"decision records    {r}")
    emit(f"gaps closed         {g} of {5 * len(specs)}")
    emit(f"findings            {f}")
    emit(f"worked rules        {len(worked.RULES)}")
    emit(f"unattended loops    {loops}")
    emit("standing creds      0")
    emit("linted by           designs.lint: method.lint + 13 rules")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="designs.demo45")
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--id")
    ap.add_argument("--fault", choices=FAULTS)
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    with internal.installed() as designs:
        specs = copy.deepcopy(designs)
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
