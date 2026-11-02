"""Seeded run transcripts as text, for the live labs.

A transcript reads like a run's history: customer messages, the
agent's turns, and tool results, most of them flight searches. Early
in it sit the facts a later step needs: a customer constraint, a
canceled approval, and the approval still pending, with its amount and
idempotency key. Everything is invented; identifiers follow the
book's formats.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded

# Measured on the small model's usage, November 2, 2026: these
# histories are dense with digits and run about 1.6 characters a token.
CHARS_PER_TOKEN = 1.6
AIRPORTS = ("ORD", "LAX", "SFO", "SEA", "BOS", "ATL", "MIA", "PHX",
            "MSP", "DTW", "AUS", "SAN")
CONSTRAINTS = (
    ("no overnight departures; I am traveling with my two children",
     "overnight"),
    ("we must land before 6 p.m.; we connect to a cruise", "6 p.m."),
    ("no connections on a second carrier, please", "second carrier"),
)


@dataclass(frozen=True)
class Facts:
    itinerary: str
    approval: str
    canceled: str
    amount: str
    key: str
    constraint: str
    marker: str        # a phrase that shows the constraint survived

    def pinned(self) -> list[str]:
        return [self.approval, self.amount, self.key]


def facts(seed: int, i: int) -> Facts:
    r = seeded(seed, "facts", str(i))
    itin = f"LTG-{5_300_000 + r.randint(0, 99_999)}"
    c, m = CONSTRAINTS[i % len(CONSTRAINTS)]
    return Facts(itin, f"APR-{r.randint(40_000, 49_999)}",
                 f"APR-{r.randint(30_000, 39_999)}",
                 f"${r.randint(12_000, 98_000) / 100:,.2f}",
                 f"idem-{itin}-rf1", c, m)


def _search(r, step: int) -> list[str]:
    a, b = r.sample(AIRPORTS, 2)
    n = r.randint(8, 22)
    rows = [f"[step {step}] tool flights.search {a}->{b} -> {n} results"]
    for _ in range(n):
        h, m = r.randint(5, 23), r.choice((0, 5, 15, 20, 35, 40, 55))
        rows.append(f"  FLT-{r.randint(900_000, 999_999)} {a} {h:02d}:"
                    f"{m:02d} -> {b} {(h + r.randint(2, 5)) % 24:02d}:"
                    f"{m:02d} fare ${r.randint(9_000, 90_000) / 100:,.2f}"
                    f" seats {r.randint(1, 9)} rule FR-{r.randint(100, 140)}")
    return rows


def _turn(r, step: int) -> str:
    return r.choice((
        f"[step {step}] agent: checking fare rules for the options.",
        f"[step {step}] agent: none of these fit yet; searching again.",
        f"[step {step}] agent: comparing arrival times for the family.",
        f"[step {step}] agent: asking the carrier for a waiver status.",
    ))


def transcript(f: Facts, seed: int, i: int, target_tokens: int) -> str:
    r = seeded(seed, "transcript", str(i), str(target_tokens))
    lines = [f"Run history for itinerary {f.itinerary}.",
             f"[step 1] customer: my flight was canceled. Please move "
             f"us to the next good option and refund the difference.",
             f"[step 2] customer: {f.constraint}.",
             f"[step 3] tool approval.request -> {f.canceled} status "
             f"canceled (superseded, wrong amount)",
             f"[step 4] tool approval.request -> {f.approval} status "
             f"pending, refund {f.amount}, key {f.key}",
             "[step 4] agent: the refund approval is pending at the "
             "desk; do not request it again."]
    step = 5
    while len("\n".join(lines)) < int(target_tokens * CHARS_PER_TOKEN):
        lines.append(_turn(r, step))
        lines.extend(_search(r, step))
        step += 1
    return "\n".join(lines)


QUESTION = (
    "Before the next step, report the state of this run. Answer with "
    "JSON only, with these keys: pending_approval (the approval ID "
    "still pending), amount (its refund amount), idempotency_key, and "
    "constraint (the customer's constraint, in a few words).")


def score(answer: str, f: Facts) -> dict:
    a = answer
    return {"approval": f.approval in a and
            not (f.canceled in a and f.approval not in a),
            "amount": f.amount in a, "key": f.key in a,
            "constraint": f.marker.lower() in a.lower()}
