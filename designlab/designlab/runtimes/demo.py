"""Chapter 30 demo: python3 -m runtimes.demo --part grid

Parts: grid, inject, features, stale, weight, drop, portable, tie,
migrate, skills. Every line printed is 70 characters or fewer.
"""
from __future__ import annotations

import argparse
import datetime as dt

from . import grid as G
from . import portability as P
from . import skills as S

SHORT = {"langsmith-deployment": "langsmith", "agentcore": "agentcore",
         "gemini-agent-runtime": "gemini", "langgraph": "lg-self",
         "ms-agent-framework": "maf-self"}
ABBR = {"action": "act", "control": "ctl", "knowledge": "knw",
        "trail": "trl", "portability": "prt"}


def table(g, weights=None):
    head = "option      " + " ".join(f"{ABBR[p]:>4}" for p in G.PLANES)
    print(head + "  total  musts")
    for o, t, failed in G.rank(g, weights):
        planes = G.by_plane(g, o)
        cells = " ".join(f"{planes[p]:>4}" for p in G.PLANES)
        musts = "fail " + ",".join(failed) if failed else "pass"
        print(f"{SHORT[o.id]:<11} {cells}  {t:>5g}  {musts}")


def part_grid(args):
    g = G.load()
    bases = {}
    for o in g.options:
        for c in o.cells.values():
            bases[c.basis] = bases.get(c.basis, 0) + 1
    n = sum(bases.values())
    print(f"grid as of {g.as_of}; {len(g.criteria)} criteria x "
          f"{len(g.options)} options = {n} cells")
    print("basis: " + ", ".join(f"{k} {v}" for k, v in sorted(
        bases.items())))
    print(f"must criteria: {' '.join(g.musts())}")
    table(g)


def part_inject(args):
    raw = G.read()
    raw["options"][1]["cells"]["K1"].pop("as_of")
    raw["options"][1]["cells"]["P2"]["as_of"] = "2026-06-24"
    raw["options"][2]["cells"]["C1"]["src"] = "a sales call"
    try:
        G.build(raw)
    except G.GridError as e:
        for line in str(e).split("; "):
            print("refused: " + line)


def part_features(args):
    try:
        G.build(G.feature_table(G.read()))
    except G.GridError as e:
        errs = str(e).split("; ")
        undated = sum("date" in x for x in errs)
        unsourced = sum("source" in x for x in errs)
        print(f"feature table: {len(errs)} errors, "
              f"{undated} undated, {unsourced} unsourced")
        print("first: " + errs[0])


def part_stale(args):
    g = G.load(today=dt.date(2026, 11, 2))
    print("read on 2026-11-02, stale after 92 days:")
    for w in g.warnings:
        print("  warn: " + w)


def part_weight(args):
    weights = {}
    for item in args.weight or []:
        plane, w = item.split("=")
        weights[{v: k for k, v in ABBR.items()}.get(plane, plane)] = float(w)
    print("weights: " + (", ".join(f"{k} x{v:g}" for k, v in
                                   weights.items()) or "none"))
    table(G.load(), weights)


def part_drop(args):
    raw = G.read()
    for item in args.drop or []:
        opt, cid = item.split(":")
        raw = G.drop(raw, opt, cid)
        print(f"re-scored {SHORT[opt]} {cid} to 0")
    table(G.build(raw))


def part_portable(args):
    c = P.check()
    for k, v in c.hashes.items():
        print(f"{k:<9} servicing 1.0.0  hash {v}")
    print(f"manifest diffs: {len(c.diffs)}; native fields: {len(c.tied)}")
    print("portable: " + ("yes" if c.ok else "no"))


def part_tie(args):
    c = P.check(overrides={"loop.resume_from": "thread_id",
                           "loop.effect_key": "session_id"})
    for k, v in c.hashes.items():
        print(f"{k:<9} servicing 1.0.0+  hash {v}")
    for t in c.tied:
        print("tied: " + t)
    print("portable: " + ("yes" if c.ok else "no"))


def part_migrate(args):
    print("200 cases on threads; 40 workers killed; finish on sessions")
    print("record   keys     moved  lost  re-asked  dupes  refused  verif")
    for record, key in (("native", "handle"), ("native", "run"),
                        ("store", "run")):
        m = P.migrate(record=record, key_from=key)
        print(f"{record:<8} {key:<8} {m.moved:>5} {m.lost:>5} "
              f"{m.reasked:>9} {m.duplicates:>6} {m.refused_dupes:>8} "
              f"{m.outcomes['verified']:>6}")
        if m.outcomes.get("mismatch"):
            print(f"{'':<17} verifier mismatches: "
                  f"{m.outcomes['mismatch']}")


def part_skills(args):
    sk = S.load_all()
    print("skill          meta  body  files  tools")
    for s in sk:
        print(f"{s.name:<14} {s.meta_tokens:>4} {s.body_tokens:>5} "
              f"{s.file_tokens:>6}  {len(s.tools())}")
    led = S.ledger(sk, {"fare-rules"})
    print(f"case uses fare-rules: {led['disclosed']} tokens disclosed, "
          f"{led['all_upfront']} upfront")
    for d in S.drift(sk):
        print("drift: " + d)


PARTS = {k[5:]: v for k, v in globals().items() if k.startswith("part_")}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS), required=True)
    ap.add_argument("--weight", action="append")
    ap.add_argument("--drop", action="append")
    args = ap.parse_args(argv)
    PARTS[args.part](args)


if __name__ == "__main__":
    main()
