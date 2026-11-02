"""The retrieval golden set: questions, the date each is asked as of,
and the passages that answer it. The relevant passage is the version in
effect on the as-of date (for a fare rule, the ticket's issue date), so
a superseded page is never relevant, however well it matches.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from common.rand import DEFAULT_SEED, seeded
from corpus.docs import (CARRIERS, PRODUCTS, TOPICS, documents,
                         in_effect)


@dataclass(frozen=True)
class Question:
    qid: str
    text: str
    as_of: date
    relevant: tuple[str, ...]
    style: str


def _as_of(rng) -> date:
    return date(2026, 5, rng.randint(1, 20))


def questions(seed: int = DEFAULT_SEED) -> list[Question]:
    rng = seeded(seed, "retrieval", "golden")
    out = []
    n = 0
    for code, name in CARRIERS:
        for topic, (title, _, says) in TOPICS.items():
            styles = rng.sample(("code", "customer", "desk", "ref"), 2)
            for style in styles:
                as_of = _as_of(rng)
                doc = in_effect(code, topic, as_of, seed)
                if doc is None:
                    continue
                prod = rng.choice(PRODUCTS)
                say = rng.choice(says)
                if style == "code":
                    text = f"{code} {title} {prod}"
                elif style == "ref":
                    text = f"{doc.facts['ref']} {prod}"
                elif style == "customer":
                    text = (f"{say[0].upper()}{say[1:]} on {name}; "
                            f"I have a {prod} fare.")
                else:
                    short = name.split()[0]
                    text = f"{short} {prod} {say}"
                n += 1
                out.append(Question(f"G{n:03d}", text, as_of,
                                    (doc.doc_id,), style))
    for d in documents(seed):
        if d.kind == "notice" and d.effective_from <= date(2026, 5, 20):
            name = dict(CARRIERS)[d.carrier]
            apt = d.topic.split("-")[1]
            n += 1
            out.append(Question(
                f"G{n:03d}", f"Is there a {name} waiver for {apt}?",
                date(2026, 5, 20), (d.doc_id,), "notice"))
    return out
