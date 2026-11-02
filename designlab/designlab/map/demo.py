"""Chapter 3 lab: the map as data.

    python3 -m map.demo
    python3 -m map.demo --today 2027-05-02      # age every claim
    python3 -m map.demo --lockin-weight 2       # weight lock-in twice

Every printed line is 70 characters or fewer.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt

from .model import GAP_IDS, MAP_FILE, build, load
from .shortlist import rank, recheck, shortlist
from .yamlish import loads

INJECTED = {
    "id": "acme-agent-cloud", "name": "Acme Agent Cloud",
    "category": "runtime", "vendor": "Acme (injected)", "status": "ga",
    "version": "service", "lock_in": 4, "cost": "per seat",
    "gaps": {"G1": "none", "G2": "claims", "G3": "claims",
             "G4": "none", "G5": "none"},
    "where": "not stated", "hides": "everything below the page",
    "claims": [{"text": "governance built in", "gap": "G2",
                "source": "https://example.com/platform"}],
}


def coverage(m) -> dict:
    out = {}
    for cat, opts in m.by_category().items():
        out[cat] = {g: sum(o.gaps[g] == "closes" for o in opts)
                    for g in GAP_IDS}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", type=dt.date.fromisoformat)
    ap.add_argument("--lockin-weight", type=float, default=1.0)
    a = ap.parse_args(argv)
    m = load(today=a.today)
    today = a.today or m.as_of
    undated = sum(1 for e in m.errors if "no as_of" in e)
    print("1. load map.yaml")
    print(f"   as_of {m.as_of}  today {today}  owner {m.owner}")
    print(f"   categories {len(m.categories)}  options {len(m.options)}"
          f"  claims {m.claim_count()}  undated {undated}")
    print(f"   errors {len(m.errors)}  warnings {len(m.warnings)}")
    print("2. options per category")
    for cat, opts in m.by_category().items():
        print(f"   {m.categories[cat]:<30}{len(opts):>3}")
    print("3. options that close each gap (closes = 2 points)")
    print("   " + f"{'category':<12}" + "".join(f"{g:>5}" for g in GAP_IDS))
    for cat, row in coverage(m).items():
        print("   " + f"{cat:<12}" +
              "".join(f"{row[g]:>5}" for g in GAP_IDS))
    print("4. warnings (the map loads; a person re-reads the page)")
    for w in m.warnings[:10]:
        print(f"   {w}")
    if len(m.warnings) > 10:
        print(f"   ... and {len(m.warnings) - 10} more")
    print(f"5. shortlist at lock-in weight {a.lockin_weight:g}")
    picks = shortlist(m, a.lockin_weight)
    for cat in ("runtime", "framework"):
        for s in rank(m, cat, a.lockin_weight):
            mark = "*" if s in picks[cat] else " "
            why = s.reason or f"lock-in {s.option.lock_in}"
            print(f"   {mark} {s.option.name[:31]:<31}"
                  f"{s.score:>5.1f}  {why}")
    again = recheck(m, picks)
    print(f"   shortlisted and stale, re-read first: {len(again)}")
    for oid in again:
        print(f"     {oid}")
    print("6. failure injection: a row with no date")
    raw = loads(MAP_FILE.read_text())
    bad = copy.deepcopy(raw)
    bad["options"].append(INJECTED)
    b = build(bad, today)
    print(f"   errors {len(b.errors)}  loaded {b.ok}")
    for e in b.errors:
        print(f"   refused: {e}")
    print("7. struck from the map")
    for s in m.struck:
        print(f"   {s['name']}: {s['reason']}")
    print(f"map: {len(m.categories)} categories, {len(m.options)} options;"
          f" {len(picks['runtime'])} runtimes and")
    print(f"     {len(picks['framework'])} frameworks shortlisted")
    return 0 if m.ok and not b.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
