"""Chapter 13 demo. Offline: every model answer is a recorded fixture.

    python3 -m models.demo contracts
    python3 -m models.demo test
    python3 -m models.demo format
    python3 -m models.demo variance
    python3 -m models.demo amount
    python3 -m models.demo drift [--inject loud|silent|alias|alias-quiet]
    python3 -m models.demo naive

`drift` exits 1 when it raises an alert, so run.sh can require that an
injected model move fails the check.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
from datetime import date
from pathlib import Path

from common.client import FixtureTransport
from common.text import emit

from . import variance
from .contract import load_contract, load_contracts, parse_json
from .drift import (EchoAs, LoudMove, SilentMove, baseline, compare,
                    lenient_last_object, lenient_reason)
from .fares import unflown_refund_cents, usd
from .record import ARCHIVE, FIX, alias_contract
from .runner import golden_cases, run_suite

TODAY = date(2026, 11, 2)


def _suite(c, d, wrap=None):
    t = FixtureTransport(FIX / d)
    return run_suite(c, wrap(t) if wrap else t)


def cmd_contracts(_a) -> int:
    emit(f"{'contract':<14}{'ver':<5}{'model':<19}{'kind':<9}"
         f"{'review by':<11}days")
    for c in load_contracts().values():
        emit(f"{c.name:<14}{c.version:<5}{c.model_id:<19}{c.id_kind:<9}"
             f"{c.review_by.isoformat():<11}{c.days_to_review(TODAY)}")
    return 0


def _row(label, c, r):
    emit(f"{label:<18}{c.version:<5}{c.prompt_hash:<13}"
         f"{r.passed:>2}/{len(r.cases):<3}{r.p95_s:>6.2f}"
         f"{r.cost_usd:>10.5f}")


def cmd_test(_a) -> int:
    emit(f"{'suite':<18}{'ver':<5}{'prompt':<13}{'pass':<6}"
         f"{'p95 s':>6}{'cost $':>10}")
    cs = load_contracts()
    bad = 0
    for name, c in cs.items():
        r = _suite(c, name)
        _row(name, c, r)
        bad += not r.ok()
    for arch in ("refund-reason-1.2", "desk-note-2.1"):
        c = load_contract(ARCHIVE / f"{arch}.toml")
        r = _suite(c, arch)
        _row(arch + "*", c, r)
        for x in r.cases:
            for v in x.violations:
                emit(f"  {x.case_id} {str(v)[:62]}")
    emit("* archived version, replayed for comparison")
    return 1 if bad else 0


def cmd_format(_a) -> int:
    old = load_contract(ARCHIVE / "desk-note-2.1.toml")
    r = _suite(old, "desk-note-2.1")
    loose = sum(lenient_last_object(x.raw or "") is not None
                for x in r.cases)
    new = load_contracts()["desk-note"]
    r2 = _suite(new, "desk-note")
    emit(f"desk-note {old.version} free text, strict contract : "
         f"{r.passed}/{len(r.cases)}")
    emit(f"desk-note {old.version} same replies, last-object parse: "
         f"{loose}/{len(r.cases)}")
    emit(f"desk-note {new.version} constrained decoding, strict  : "
         f"{r2.passed}/{len(r2.cases)}")
    bad = next(x for x in r.cases if not x.passed)
    emit(f"first rejected reply, {bad.case_id}, tail:")
    tail = [ln for ln in (bad.raw or "").splitlines() if ln.strip()]
    for ln in tail[:3]:
        emit("  " + ln[:66])
    return 0


def _spread(path, keys):
    meta, samples = variance.load(path)
    c = dataclasses.replace(load_contracts()["refund-reason"],
                            model_id=meta["model"], expect_echo=meta["model"])
    inputs = {x["id"]: x["input"] for x in golden_cases(c)}
    return meta, variance.spread(c, samples, keys, inputs)


def cmd_variance(_a) -> int:
    keys = ("reason_code", "needs_person")
    emit(f"{'run':<14}{'case':<7}{'n':>3}{'texts':>6}{'decisions':>10}"
         f"{'top':>6}{'ok':>4}")
    for tag in ("small", "dated-t0", "dated-t1"):
        meta, rows = _spread(FIX / f"variance-{tag}.json", keys)
        for s in rows:
            emit(f"{tag:<14}{s.case:<7}{s.n:>3}{s.texts:>6}"
                 f"{len(s.decisions):>10}{s.top_share:>6.0%}"
                 f"{s.contract_ok:>4}")
    meta, rows = _spread(FIX / "variance-small.json", keys)
    for s in rows:
        if len(s.decisions) > 1:
            emit(f"{s.case} decisions: " + "; ".join(
                f"{k[0]}/{k[1]} x{v}" for k, v in s.decisions.items()))
    return 0


def cmd_amount(_a) -> int:
    cases = {json.loads(ln)["id"]: json.loads(ln) for ln in
             (Path(__file__).parent / "golden" / "amount-cases.jsonl")
             .read_text().splitlines() if ln.strip()}
    emit(f"{'model':<8}{'case':<7}{'tool':>10}  model answers")
    for tag in ("mid", "small"):
        _meta, samples = variance.load(FIX / f"variance-amount-{tag}.json")
        for cid, case in cases.items():
            tool = usd(unflown_refund_cents(**case["fare"]))[1:]
            got = [(parse_json(s["text"]) or {}).get("refund_amount")
                   for s in samples if s["case"] == cid]
            counts = {}
            for g in got:
                counts[g] = counts.get(g, 0) + 1
            shown = ", ".join(f"{k} x{v}" for k, v in counts.items())
            emit(f"{tag:<8}{cid:<7}{tool:>10}  {shown}"[:70])
    return 0


def cmd_drift(a) -> int:
    if a.inject in ("alias", "alias-quiet"):
        c = alias_contract()
        base = baseline(c, _suite(c, "alias-before"))
        wrap = ((lambda t: EchoAs(t, base.echo))
                if a.inject == "alias-quiet" else None)
        r = _suite(c, "alias-moved", wrap)
    else:
        c = load_contracts()["refund-reason"]
        base = baseline(c, _suite(c, "refund-reason"))
        wrap = {"none": None, "loud": LoudMove,
                "silent": SilentMove}[a.inject]
        r = _suite(c, "refund-reason", wrap)
    emit(f"baseline {c.name} {base.version} prompt {base.prompt} "
         f"{base.passed}/{base.total}")
    emit(f"  echo {base.echo}")
    emit(f"run      inject={a.inject} {r.passed}/{len(r.cases)} pass "
         f"the full contract")
    codes = {}
    for x in r.cases:
        for v in x.violations:
            codes[v.code] = codes.get(v.code, 0) + 1
    if codes:
        emit("  violations: " + ", ".join(
            f"{k} x{n}" for k, n in sorted(codes.items())))
    alerts = compare(c, base, r)
    for al in alerts:
        emit(f"ALERT {al.code} -> {al.to}")
        emit(f"  {al.detail}"[:70])
    if not alerts:
        emit("no alert")
    return 1 if alerts else 0


def cmd_naive(_a) -> int:
    c = load_contracts()["refund-reason"]
    t = SilentMove(FixtureTransport(FIX / "refund-reason"))
    r = run_suite(c, t)
    mapped = [lenient_reason(c, x.raw or "") for x in r.cases]
    other = sum(code == "other" for code, _ in mapped)
    emit(f"silent move, {len(r.cases)} golden cases")
    emit(f"lenient parser: {other} mapped to 'other', 0 errors raised")
    emit(f"contract check: {len(r.cases) - r.passed} rejected, "
         f"alert to {c.alert_to}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    for n in ("contracts", "test", "format", "variance", "amount",
              "naive"):
        sub.add_parser(n)
    d = sub.add_parser("drift")
    d.add_argument("--inject", default="none",
                   choices=["none", "loud", "silent", "alias",
                            "alias-quiet"])
    a = ap.parse_args(argv)
    fn = {"contracts": cmd_contracts, "test": cmd_test,
          "format": cmd_format, "variance": cmd_variance,
          "amount": cmd_amount, "drift": cmd_drift, "naive": cmd_naive,
          None: cmd_test}[a.cmd]
    return fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
