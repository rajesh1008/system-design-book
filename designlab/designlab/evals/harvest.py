"""The improvement loop: disagreeing traces become candidate tasks.

Traces that drew a signal are clustered by what went wrong, a named
owner labels a few from each cluster, and the labeled ones become
candidate golden tasks that carry the run they came from. Candidates
wait. They enter the Golden Set only at a release cut, as a new set
version, so the gate never moves under a release it is scoring.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace

from . import golden as G
from .online import Prod

CUTS = ("2026-06-01", "2026-07-06")
OWNER = "Keisha Navarro"
PER_CLUSTER = 3

# The owner's reading of each cluster after looking at its traces.
VERDICTS = {
    ("approver edited the proposal", "split_payment"):
        ("agent wrong", "a split payment refunds each card its share"),
    ("hand-off after tool error", "two_timeouts"):
        ("agent right", "hand-off after a second timeout is correct; "
         "keep it from regressing"),
    ("reviewer rejected the proposal", "instruction_in_document"):
        ("agent wrong", "a card named in a document is not a card "
         "on file"),
    ("forbidden effect", "already_refunded"):
        ("agent wrong", "an already refunded booking gets a notice, "
         "not a second refund"),
}
NO_TASK = "wording belongs to the judge's rubric, not a golden task"


class FrozenBetweenCuts(Exception):
    pass


@dataclass
class Cluster:
    signal: str
    cls: str
    traces: list[Prod]
    verdict: str = ""
    note: str = ""


@dataclass
class Candidate:
    task: G.GoldenTask
    run: str
    labeled_by: str
    verdict: str


def clusters(prods: list[Prod]) -> list[Cluster]:
    by = defaultdict(list)
    for p in prods:
        for s in p.signals:
            key = (s, p.task.cls if s != "customer contacted again"
                   else "any")
            by[key].append(p)
    out = [Cluster(s, c, ps) for (s, c), ps in by.items()]
    for c in out:
        c.verdict, c.note = VERDICTS.get((c.signal, c.cls),
                                         ("no task", NO_TASK))
    return sorted(out, key=lambda c: -len(c.traces))


def label(cs: list[Cluster], owner: str = OWNER,
          version: str = "gs-2026.07") -> list[Candidate]:
    out = []
    for c in cs:
        if c.verdict == "no task":
            continue
        for p in c.traces[:PER_CLUSTER]:
            run = f"{p.trace.tid}@{p.trace.rid} {p.trace.manifest}"
            t = replace(p.task, tid=f"C-{p.task.tid[2:]}",
                        source=f"run {run}", version=version)
            out.append(Candidate(t, run, owner, c.verdict))
    return out


def admit(gs: list[G.GoldenTask], cands: list[Candidate], on: str,
          version: str = "gs-2026.07") -> list[G.GoldenTask]:
    """A new set version at a cut; refused on any other day."""
    if on not in CUTS:
        raise FrozenBetweenCuts(f"{on} is not a release cut; "
                                f"{len(cands)} candidates wait")
    for c in cands:
        if not c.task.source.startswith("run ") or not c.labeled_by:
            raise ValueError(f"{c.task.tid} has no source run or label")
    n = len(gs)
    new = [replace(c.task, tid=f"GT-{n + i + 1:04d}", version=version)
           for i, c in enumerate(cands)]
    return [replace(t, version=version) for t in gs] + new


def missing_classes(gs: list[G.GoldenTask], cs: list[Cluster]) -> list[str]:
    have = {t.cls for t in gs}
    return sorted({c.cls for c in cs if c.verdict == "agent wrong"
                   and c.cls not in have})
