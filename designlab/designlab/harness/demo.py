"""Chapter 25 demos. Offline and seeded; every line fits 70 characters.

    python3 -m harness.demo --case manifest|may28|deploy|description|
                                   shapes|suite|trail
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter

from common.text import emit
from common.trail import check_trail

from . import deploy, loops, suite
from . import manifest as M
from .tools import PASTED, catalog
from .world import cases

OLD_PIN = ["permission_ids", "idempotency_keys", "amounts"]
BUILD = "2026.05.26-1"        # what the trail called the harness in May


def case_manifest(name="servicing-1.0.0"):
    h = M.resolve(M.load(name))
    c = M.counts(h)
    emit(f"manifest {h['name']} {h['version']}  "
         f"hash {M.short(M.manifest_hash(h))}")
    emit(f"loop shape  {h['loop']['shape']}")
    emit(f"tools       {c['tools']} ({c['effect_tools']} with effects)")
    for t in h["tools"]:
        emit(f"  {t['name']:18} {t['version']:4} {t['kind']}")
    cx = h["context"]
    emit(f"context     {cx['budget_tokens']:,} tokens, compact at "
         f"{cx['compact_at']:.0%}, keep {cx['keep_turns']} turns")
    emit(f"  pinned    {', '.join(cx['pin'][:3])},")
    emit(f"            {', '.join(cx['pin'][3:])}")
    emit(f"stops       {', '.join(s['id'] for s in h['stops'])}")
    b = h["budgets"]
    emit(f"budgets     {b['steps']} steps, {b['model_calls']} model "
         f"calls, ${b['task_usd']}, {b['tool_retries']} retry")


def _night(h, cs):
    hz = loops.Harness(h, trail=loops.new_trail())
    runs = [loops.react(c, hz, seed=1) for c in cs]
    return hz, runs


def case_may28():
    base = M.resolve(M.load("servicing-1.0.0"))
    may27 = M.apply_overrides(base, {"version": BUILD,
                                     "context.pin": OLD_PIN})
    may28 = M.apply_overrides(may27, {"context.keep_turns": 3})
    cs = cases(1000)
    emit("1,000 refund conversations, same cases, same seeds, same model")
    emit(f"{'':18}{'keep':>5}{'re-asked':>10}{'handed off':>12}"
         f"{'hash':>14}")
    rows = {}
    for label, h in (("May 27 settings", may27),
                     ("May 28 settings", may28)):
        hz, runs = _night(h, cs)
        asked = sum(r.reasks > 0 for r in runs)
        off = sum(r.stop == "customer_asked" for r in runs)
        rows[label] = (hz, runs)
        emit(f"{label:18}{h['context']['keep_turns']:>5}{asked:>10}"
             f"{off:>12}{hz.hash:>14}")
    for label, (hz, _) in rows.items():
        line = json.loads(hz.trail.lines[0])
        emit(f"trail, {label[:6]}: harness={line['harness']} "
             f"manifest={line['manifest']}")
    emit(f"changed: {', '.join(M.diff(may27, may28))}")
    emit("without the manifest field, the two nights' lines read the same")


def case_deploy():
    reg = deploy.releases()
    emit("registered releases:")
    for v, r in reg.items():
        emit(f"  {v:8} {r['hash'][:12]}  {r['status']}")
    tries = [
        ("1.0.0 as built", "servicing-1.0.0", {}),
        ("1.0.0 + settings", "servicing-1.0.0",
         {"context.keep_turns": 3}),
        ("first test build", "servicing-1.0.0-rc1", {}),
        ("refund machine", "servicing-1.1.0", {}),
        ("no version", "servicing-1.0.0", {"version": ""}),
    ]
    for label, name, ov in tries:
        v = deploy.check(M.load(name), ov)
        word = "deploy" if v.ok else "REFUSE"
        emit(f"{word}  {label:18} {v.reason}")


def case_description():
    h = M.resolve(M.load("servicing-1.0.0"))
    old = catalog()
    d = old["rebook_ticket"]["description"]
    old["rebook_ticket"] = dict(old["rebook_ticket"],
                                description=d.replace(" " + PASTED, ""))
    before = M.resolve(M.load("servicing-1.0.0"), tools=old)
    emit(f"rebook_ticket version, before and after: "
         f"{before['tools'][8]['version']} and {h['tools'][8]['version']}")
    emit(f"manifest hash before  {M.short(M.manifest_hash(before))}")
    emit(f"manifest hash after   {M.short(M.manifest_hash(h))}")
    for p in M.diff(before, h):
        emit(f"changed: {p}")
    emit("the tool's version holds; the harness version moves")


def _summ(runs):
    st = sorted(r.steps for r in runs)
    cost = sorted(r.cost for r in runs)
    n = len(runs)
    return (st[0], int(statistics.median(st)), st[int(0.95 * n) - 1],
            st[-1], sum(r.illegal for r in runs),
            sum(r.illegal > 0 for r in runs), cost[n // 2])


def case_shapes():
    h = M.resolve(M.load("servicing-1.1.0"))
    cs = cases(1000)
    hz = loops.Harness(h)
    react = [loops.react(c, hz) for c in cs]
    sm = [loops.state_machine(c, hz) for c in cs]
    emit("1,000 replayed refund cases, one harness, two loop shapes")
    emit(f"{'':15}{'min':>5}{'med':>5}{'p95':>5}{'max':>5}"
         f"{'illegal':>9}{'runs':>6}{'cost med':>10}")
    for label, rs in (("ReAct", react), ("state machine", sm)):
        a, m, p, z, ill, nr, cm = _summ(rs)
        emit(f"{label:15}{a:>5}{m:>5}{p:>5}{z:>5}{ill:>9}{nr:>6}"
             f"{'$' + format(cm, '.4f'):>10}")
    names = {"refused: no permission": "execute before permission",
             "outcome not verified": "notify before verify",
             "duplicate: no new effect": "execute twice"}
    kinds = Counter(names.get(x, x) for r in react for x in r.refused)
    for k, n in kinds.most_common():
        emit(f"  ReAct, refused by gateway: {k:26} {n:>4}")
    for label, rs in (("ReAct", react), ("state machine", sm)):
        out = Counter(r.outcome for r in rs)
        emit(f"{label:15} done {out['done']}, declined "
             f"{out['declined']}, handed off {out['handed_off']}")
    one = next(c for c in cs if c.eligible and c.approve)
    st = [loops.react(one, hz, seed=i).steps for i in range(1000)]
    emit(f"case {one.cid} under ReAct, 1,000 seeds: {min(st)} to "
         f"{max(st)} steps")
    allowed, forbidden = loops.transitions(h)
    emit(f"transition table: {len(allowed)} allowed, "
         f"{len(forbidden)} forbidden")


def case_suite(name):
    h = M.resolve(M.load(name))
    res = suite.run(h)
    bad = [r for r in res if r[2]]
    emit(f"harness {h['version']}: {len(res) - len(bad)} of {len(res)} "
         f"checks pass")
    for g, fn, why in res:
        mark = "FAIL" if why else "ok  "
        emit(f"{mark} {g:12} {fn}"[:70])
        if why:
            emit(f"       {why}"[:70])


def case_trail():
    h = M.resolve(M.load("servicing-1.1.0"))
    hz = loops.Harness(h, trail=loops.new_trail())
    c = next(c for c in cases(20) if c.eligible and c.approve)
    loops.state_machine(c, hz)
    for line in hz.trail.lines:
        e = json.loads(line)
        emit(f"{e['at'][11:19]} {e['step']} {e.get('state', e['what']):8}"
             f" -> {e.get('next', e.get('outcome', '')):10} "
             f"{e['harness']} {e['manifest']}")
    emit(f"trail links: {check_trail(hz.trail.lines) or 'all intact'}")
    emit(f"lines without a manifest hash: "
         f"{sum('manifest' not in json.loads(x) for x in hz.trail.lines)}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--case", default="manifest")
    p.add_argument("--manifest", default="servicing-1.0.0")
    a = p.parse_args(argv)
    if a.case == "manifest":
        case_manifest(a.manifest)
    elif a.case == "suite":
        case_suite(a.manifest)
    else:
        {"may28": case_may28, "deploy": case_deploy,
         "description": case_description, "shapes": case_shapes,
         "trail": case_trail}[a.case]()


if __name__ == "__main__":
    main()
