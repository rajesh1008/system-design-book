"""Research tasks for the agentic loop: agent-desk questions that need
one to three facts (slots), each from an admissible source in effect on
the case's as-of date. A few cannot be answered from the corpus; the
right outcome for those is a hand-off, not an answer.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from common.rand import DEFAULT_SEED, seeded
from corpus.docs import CARRIERS, NOTICE_EVENTS, PRODUCTS, TOPICS, by_id


@dataclass(frozen=True)
class Slot:
    carrier: str
    topic: str
    product: str

    def label(self) -> str:
        return f"{self.carrier} {self.topic} {self.product}"


@dataclass(frozen=True)
class Task:
    tid: str
    question: str
    as_of: date
    slots: tuple[Slot, ...]
    answerable: bool


def _has_notice(code: str, apt: str, seed: int) -> bool:
    return f"NT-{code}-{apt}" in by_id(seed)


def tasks(seed: int = DEFAULT_SEED, n: int = 40) -> list[Task]:
    rng = seeded(seed, "retrieval", "tasks")
    topics = list(TOPICS)
    out = []
    for k in range(n):
        code, name = rng.choice(CARRIERS)
        prod = rng.choice(PRODUCTS)
        as_of = date(2026, 5, rng.randint(1, 20))
        shape = rng.random()
        if shape < 0.40:
            t = rng.choice(topics)
            q = (f"{name}, {prod} fare: "
                 f"{rng.choice(TOPICS[t][2])}. What applies?")
            slots = (Slot(code, t, prod),)
        elif shape < 0.75:
            t1, t2 = rng.sample(topics, 2)
            q = (f"{name}, {prod} fare. Customer says: "
                 f"{rng.choice(TOPICS[t1][2])}; also, "
                 f"{rng.choice(TOPICS[t2][2]).lower()}. What applies?")
            slots = (Slot(code, t1, prod), Slot(code, t2, prod))
        else:
            apt = rng.choice([e[0] for e in NOTICE_EVENTS[:3]])
            q = (f"Does the {name} waiver for {apt} cover a {prod} fare, "
                 f"and what is the change fee after it?")
            slots = (Slot(code, f"waiver-{apt}", prod),
                     Slot(code, "change-fee", prod))
        answerable = all(not s.topic.startswith("waiver")
                         or _has_notice(s.carrier, s.topic[7:], seed)
                         for s in slots)
        out.append(Task(f"T{k + 1:02d}", q, as_of, slots, answerable))
    return out


# The shadow question from April 29, 2026, in the lab's corpus: a
# waiver that does not exist for this carrier, asked about partners.
RUNAWAY = Task("T00", "Does the Prairie Airways waiver for ORD cover "
               "Basic fares booked through a partner airline?",
               date(2026, 4, 29), (Slot("XPA", "waiver-ORD", "Basic"),),
               False)
