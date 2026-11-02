"""Preference pairs from the approver's corrections.

Six months of refund cards from the approver desk, December 2025 to
May 2026. When the approver rewrites the refund reason and changes
nothing else, the agent's draft and the approver's text form a pair
(rejected, chosen). When the approver changes the amount, the kind
(refund or credit), or the decision, the correction is policy, not
preference, and the card is dropped. An unedited approval is not a
pair either: on a busy desk it is as often a wave-through as a
preference. The ranking model is a Bradley-Terry logistic regression on
the difference of two reasons' features: the stand-in for a model tuned
on pairs, small enough to read.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from common.rand import seeded

from .data import MONTHS

CODES = {"involuntary_refund": "INVOL", "cancel_refund": "VOL",
         "ancillary_refund": "ANC"}
RULES = {"INVOL": "FR-112", "VOL": "FR-031", "ANC": "FR-207"}
FACTS = {
    "INVOL": ["departure moved {h}h{m:02d}m", "flight canceled by carrier",
              "connection broken by schedule change"],
    "VOL": ["customer canceled {d} days out", "plans changed, refundable "
            "fare", "canceled within 24 hours"],
    "ANC": ["seat fee charged, seat not given", "bag fee charged twice",
            "wifi bought, not delivered"],
}
NARRATIVE = "The customer requested a refund because {fact}."
SPECULATE = [" The customer probably misread the fare rules.",
             " It seems the customer may be at fault.",
             " Customer claims this happened."]
PADDING = " We apologize for any inconvenience this may have caused."


@dataclass(frozen=True)
class Card:
    card_id: str
    month: str
    code: str
    draft: str
    final: str
    amount_changed: bool
    kind_changed: bool
    rejected: bool
    queue: int              # cards waiting when this one was decided
    defect: bool            # the draft broke the house wording


def house(code: str, fact: str) -> str:
    return f"{code}: {fact}; rule {RULES[code]}"


def cards(seed: int = 17, per_month: int = 2400) -> list[Card]:
    out = []
    n = 0
    for month in MONTHS:
        rng = seeded(seed, "adapt", "prefs", month)
        for _ in range(per_month):
            n += 1
            code = rng.choices(list(RULES), weights=[190, 210, 80])[0]
            fact = rng.choice(FACTS[code]).format(
                h=rng.randint(1, 4), m=rng.choice((0, 15, 30, 45)),
                d=rng.randint(2, 40))
            good = house(code, fact)
            r = rng.random()
            if r < 0.84:
                draft, defect = good, False
            elif r < 0.93:
                draft, defect = NARRATIVE.format(fact=fact), True
            elif r < 0.97:
                draft = good + rng.choice(SPECULATE)
                defect = True
            else:
                draft, defect = good + PADDING, True
            queue = rng.choice((2, 5, 10, 20, 40, 60))
            catch = 0.97 if queue < 20 else 0.70 if queue < 40 else 0.45
            amount = rng.random() < 0.025
            kind = rng.random() < 0.008
            rejected = rng.random() < 0.006
            edited = defect and rng.random() < catch
            final = good if (edited or not defect) else draft
            if not defect and rng.random() < 0.01:
                # a second approver who prefers the long form
                final = NARRATIVE.format(fact=fact)
            out.append(Card(f"RC{n:06d}", month, code, draft, final,
                            amount, kind, rejected, queue, defect))
    return out


@dataclass(frozen=True)
class Pair:
    card_id: str
    month: str
    rejected: str
    chosen: str


def export(cs: list[Card]) -> tuple[list[Pair], Counter]:
    """Pairs from wording-only edits; a count of what was dropped."""
    pairs, dropped = [], Counter()
    for c in cs:
        if c.draft == c.final:
            dropped["unedited"] += 1
        elif c.amount_changed or c.kind_changed or c.rejected:
            dropped["effect changed"] += 1
        else:
            pairs.append(Pair(c.card_id, c.month, c.draft, c.final))
    return pairs, dropped


HOUSE = re.compile(r"^[A-Z]+: .+; rule FR-\d{3}$")
SPEC = re.compile(r"probably|seems|may be|claims")


def features(text: str) -> dict[str, float]:
    return {"house": float(bool(HOUSE.match(text))),
            "rule_id": float("rule FR-" in text),
            "speculates": float(bool(SPEC.search(text))),
            "apology": float("apologize" in text),
            "narrative": float(text.startswith("The customer")),
            "words": len(text.split()) / 20.0}


@dataclass
class Ranker:
    w: dict[str, float]

    @classmethod
    def train(cls, pairs: list[Pair], epochs: int = 20,
              rate: float = 0.3) -> "Ranker":
        w: dict[str, float] = {}
        for _ in range(epochs):
            for p in pairs:
                fc, fr = features(p.chosen), features(p.rejected)
                d = {k: fc[k] - fr[k] for k in fc}
                z = sum(w.get(k, 0.0) * v for k, v in d.items())
                g = 1.0 / (1.0 + math.exp(-z)) - 1.0
                for k, v in d.items():
                    w[k] = w.get(k, 0.0) - rate * g * v
        return cls(w)

    def score(self, text: str) -> float:
        return sum(self.w.get(k, 0.0) * v
                   for k, v in features(text).items())

    def prefers(self, p: Pair) -> bool:
        return self.score(p.chosen) > self.score(p.rejected)


def rule_fix(text: str, code: str) -> str:
    """The cheap fix: rewrite a narrative reason into the house format."""
    m = re.match(r"The customer requested a refund because (.+)\.$", text)
    if m:
        return house(code, m.group(1))
    return text


def wave_through(cs: list[Card]) -> list[tuple[str, int, float]]:
    """Share of defective drafts approved unedited, by queue depth."""
    rows = []
    for name, lo, hi in (("under 20", 0, 20), ("20 to 39", 20, 40),
                         ("40 or more", 40, 10**6)):
        d = [c for c in cs if c.defect and lo <= c.queue < hi]
        passed = sum(c.final == c.draft for c in d)
        rows.append((name, len(d), passed / len(d) if d else 0.0))
    return rows
