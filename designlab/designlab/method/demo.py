"""Chapter 5 demo: lint three designs, recompute an estimate, inject a
failure, and print the review checklist.

    python3 -m method.demo
    python3 -m method.demo --lint PATH          lint one design file
    python3 -m method.demo --question ID=TEXT   add a bank question

No model calls and no randomness: the same files give the same output.
"""
from __future__ import annotations

import argparse
import copy
import sys

from common.text import emit

from .artifacts import ARTIFACTS, QUESTIONS
from .design import from_dict, load
from .lint import checklist, lint


def _fmt(v: float) -> str:
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _summary(name: str, findings, rows) -> str:
    ok = sum(1 for r in rows if r[3])
    word = "finding" if len(findings) == 1 else "findings"
    return f"   {name}: {len(findings)} {word}; checklist {ok} of " \
           f"{len(rows)} pass"


def lint_one(path: str, questions) -> int:
    d = load(path)
    found = lint(d, questions)
    for f in found:
        emit(f"   {f.line()}"[:70])
    emit(_summary(d.meta.get("version", path), found, checklist(found)))
    return 1 if found else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="method.demo")
    ap.add_argument("--lint", metavar="PATH")
    ap.add_argument("--question", metavar="ID=TEXT")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    questions = dict(QUESTIONS)
    if a.question:
        qid, _, text = a.question.partition("=")
        questions[qid.strip()] = text.strip()
    if a.lint:
        return lint_one(a.lint, questions)

    emit("1. the eight artifacts of a checkable design")
    for i, (_, name, q) in enumerate(ARTIFACTS, 1):
        emit(f"   {i} {name:<16} {q}")

    if a.question:
        emit(f"2. bank question added: {qid.strip()}")
        for name in ("demo-2025-10-06", "v0", "v0_1"):
            d = load(name)
            found = lint(d, questions)
            hit = [f for f in found if f.where == f"req {qid.strip()}"]
            emit(f"   {name:<16} findings {len(found):>2}; "
                 f"new question {'fails' if hit else 'n/a'}")
        return 0

    emit("2. lint the October 6 demo, written down as a design")
    demo = load("demo-2025-10-06")
    found = lint(demo)
    have = sum(1 for k, _, _ in ARTIFACTS if demo.section(k))
    emit(f"   artifacts present: {have} of {len(ARTIFACTS)}")
    rules: dict[str, int] = {}
    for f in found:
        rules[f.rule.split("-")[0]] = rules.get(f.rule.split("-")[0], 0) + 1
    emit("   " + ", ".join(f"{k} {v}" for k, v in sorted(rules.items())))
    emit(_summary("demo", found, checklist(found)))

    v0 = load("v0")
    emit(f"3. lint v0 ({v0.meta['author']}, {v0.meta['as_of']})")
    f0 = lint(v0)
    for f in f0:
        emit(f"   {f.line()}"[:70])
    emit(_summary("v0", f0, checklist(f0)))

    v1 = load("v0_1")
    emit(f"4. the estimate sheet, v0.1 ({v1.meta['as_of']})")
    for ln in v1.lines:
        kind = "in " if "formula" not in ln else "=  "
        emit(f"   {kind}{ln['name']:<20} {_fmt(v1.values[ln['name']]):>10}"
             f"  {ln['unit']}"[:70])
    emit(f"   v0 said peak_requests_per_s = 2,000; v0.1 computes "
         f"{_fmt(v1.values['peak_requests_per_s'])}")

    emit("5. sensitivity: each input at its stated low and high")
    for target in ("reviewers_needed", "peak_requests_per_s"):
        emit(f"   {target} (base {_fmt(v1.values[target])})")
        for n, lo, hi in v1.sensitivity(target)[:3]:
            emit(f"     {n:<18} {_fmt(lo):>6} to {_fmt(hi):>6}")

    emit("6. lint v0.1")
    f1 = lint(v1)
    for f in f1:
        emit(f"   {f.line()}"[:70])
    emit(_summary("v0.1", f1, checklist(f1)))
    recs = v1.section("records")
    norev = sum(1 for r in recs if not r.get("reverse_if"))
    dec = v1.section("decisions")[0]
    emit(f"   decision {dec['id']}: {len(dec['options'])} options, "
         f"chose {dec['chosen']}")
    emit(f"   records {len(recs)}, {norev} without a reversal condition")

    emit("7. failure injection: drop the assumption on storm_days")
    raw = copy.deepcopy(v1.raw)
    for ln in raw["estimate"]:
        if ln["name"] == "storm_days":
            ln["assumption"] = ""
    fi = lint(from_dict(raw))
    for f in fi:
        emit(f"   {f.line()}"[:70])
    emit(_summary("v0.1 injected", fi, checklist(fi)))

    emit("8. review checklist, v0 then v0.1")
    for r0, r1 in zip(checklist(f0), checklist(f1)):
        s0 = "pass" if r0[3] else "FAIL"
        s1 = "pass" if r1[3] else "FAIL"
        emit(f"   {r0[0]} {r0[2]:<44} {s0} {s1}")

    fixed = len(f0) - len(f1)
    emit(f"method: {len(ARTIFACTS)} artifacts, 1 linter; v0 fails "
         f"{len(f0)} checks, v0.1 passes" if not f1 and fixed else
         "method: v0.1 still fails")
    return 0 if not f1 and len(fi) == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
