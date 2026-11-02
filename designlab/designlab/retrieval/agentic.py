"""Agentic retrieval: the agent plans, issues and refines queries in a
loop, within a budget, until a verifier says the evidence is sufficient
or the budget runs out and a person takes the case.

Three parts, each replaceable:
  planner   proposes the next query (scripted here; a model in live.py)
  verifier  code, not the model: every slot the task needs has an
            admissible passage, in effect on the as-of date, from the
            carrier and topic the slot names
  budget    queries per task; at the budget the loop hands off with the
            evidence it has, or (to show the cost) answers anyway
  cite      "verified": the answer may cite only passages the verifier
            accepted; "read": anything the loop read (the pilot's way)

inject="no-stop" removes the verifier and the budget: the loop runs
until the planner has nothing new to try. That is the April 29 loop.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common.rand import seeded
from corpus.docs import CARRIERS, TOPICS

from .hybrid import search
from .tasks import Slot, Task

PER_QUERY = 5          # passages read per query


def admissible(doc, slot: Slot, as_of) -> bool:
    return (doc.kind in ("fare-rule", "notice")
            and doc.carrier == slot.carrier and doc.topic == slot.topic
            and doc.in_effect(as_of))


def unmet(task: Task, evidence: list) -> list[Slot]:
    return [s for s in task.slots
            if not any(admissible(h.doc, s, task.as_of) for h in evidence)]


def _phrases(slot: Slot) -> list[str]:
    if slot.topic.startswith("waiver"):
        apt = slot.topic[7:]
        return [f"waiver {apt}", f"travel waiver {apt}",
                f"weather waiver {apt} change", f"{apt} storm waiver",
                f"{apt} fee waiver partner booking"]
    title, _, says = TOPICS[slot.topic]
    return [title] + list(says)


class ScriptedPlanner:
    """Stands in for the model. The first query is the question as
    asked; later ones aim at a slot the verifier says is still unmet,
    phrased the way a model tends to: sometimes the rule's words,
    sometimes the customer's. Seeded, so runs repeat."""

    def __init__(self, seed: int = 19):
        self.seed = seed

    def queries(self, task: Task, gaps):
        rng = seeded(self.seed, "planner", task.tid)
        yield task.question
        tried = {task.question}
        while True:
            slots = gaps()
            if not slots:
                slots = list(task.slots)
            slot = slots[0]
            name = dict(CARRIERS)[slot.carrier]
            names = [name, slot.carrier, name.split()[0]]
            options = [f"{n} {p}" for n in names for p in _phrases(slot)]
            # A model also drops the carrier now and then.
            options += list(_phrases(slot)) * 2
            options += [f"{o} {slot.product}" for o in options]
            fresh = sorted({o for o in options if o not in tried},
                           key=options.index)
            fresh = [o for o in options if o in set(fresh)]
            if not fresh:
                return
            q = rng.choice(fresh)
            tried.add(q)
            yield q


@dataclass
class Run:
    task: Task
    queries: list[str] = field(default_factory=list)
    evidence: list = field(default_factory=list)
    stop: str = ""
    answer: list = field(default_factory=list)   # (slot, doc or None)

    @property
    def handed_off(self) -> bool:
        return not self.answer


def run(task: Task, budget: int | None = 8, planner=None,
        use_rerank: bool = True, dates: str = "pre",
        at_budget: str = "handoff", inject: str | None = None,
        cite: str = "verified") -> Run:
    planner = planner or ScriptedPlanner()
    if inject == "no-stop":
        budget, verify = None, False
    else:
        verify = True
    r = Run(task)
    seen = set()
    gen = planner.queries(task, lambda: unmet(task, r.evidence))
    for q in gen:
        if budget is not None and len(r.queries) >= budget:
            r.stop = "budget"
            break
        r.queries.append(q)
        for h in search(q, task.as_of, k=PER_QUERY, use_rerank=use_rerank,
                        dates=dates):
            if h.doc.doc_id not in seen:
                seen.add(h.doc.doc_id)
                r.evidence.append(h)
        if verify and not unmet(task, r.evidence):
            r.stop = "verified"
            break
    else:
        r.stop = "exhausted"
    if r.stop in ("verified", "exhausted") or at_budget == "answer":
        pool = r.evidence
        if cite == "verified":
            # The answer step sees only passages the verifier accepted.
            pool = [h for h in r.evidence
                    if any(admissible(h.doc, s, task.as_of)
                           for s in task.slots)]
        r.answer = compose(task, pool)
    return r


def _mentions(slot: Slot) -> list[str]:
    if slot.topic.startswith("waiver"):
        return ["waiver", slot.topic[7:]]
    return [TOPICS[slot.topic][0]]


def compose(task: Task, evidence: list) -> list:
    """The answer step, scripted. For each slot it cites the first
    passage it read that names the carrier and the slot's topic, the
    way a model leans on what it read first. Help articles name no
    carrier, so they are never cited; a desk note can be."""
    out = []
    for s in task.slots:
        name = dict(CARRIERS)[s.carrier]
        cands = [h.doc for h in evidence
                 if name in h.doc.text
                 and all(m.lower() in h.doc.text.lower()
                         for m in _mentions(s))]
        out.append((s, cands[0] if cands else None))
    return out


def check_budget(runs: list[Run], budget: int) -> list[str]:
    """The budget test: no task may issue more queries than the budget."""
    return [f"{r.task.tid} issued {len(r.queries)} queries"
            for r in runs if len(r.queries) > budget]
