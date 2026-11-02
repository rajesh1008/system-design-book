"""Teacher labels: the frontier model labels change requests.

Live, through common.client: ten messages a call, the frontier role as
the teacher and the small role, with the same prompt, as the "try the
context first" baseline. Responses are cached under adapt/fixtures, so
a second run costs nothing and the offline demo replays the same
labels. Reads ANTHROPIC_API_KEY from the environment through
common.client and never prints it.

The thousands of other training labels come from `sim_teacher`, which
behaves like the recorded frontier labels: right on clear messages
apart from a small slip rate between neighbor types (twice as high on
shorthand), and "unclear" on vague ones.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from common.client import FixtureTransport, ModelClient
from common.rand import seeded
from common.spend import SpendMeter

from .data import TYPES, UNCLEAR, Message

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BATCH = 10
# Output tokens a message. The small model may think before it answers;
# at 24 a message it ran out on six of ten calls, so it gets more room.
MAX_TOKENS = {"frontier": 24, "small": 100}

DEFINITIONS = {
    "voluntary_rebook": "customer wants a different flight or date",
    "cancel_credit": "customer cancels and keeps the value as credit",
    "involuntary_rebook": "airline changed or canceled; customer "
                          "wants another flight",
    "hotel_cancel": "cancel the hotel only",
    "cancel_refund": "customer cancels and wants money back",
    "involuntary_refund": "airline changed or canceled; customer "
                          "wants money back",
    "upgrade": "buy a better cabin or seat class",
    "accept_schedule": "customer accepts an airline schedule change",
    "hotel_date_change": "change hotel nights",
    "ancillary_refund": "refund a seat, bag, or other extra",
    "car_change": "change a rental car",
    "name_correction": "fix a passenger name",
}

SYSTEM = ("You classify Lakeshore Travel Group change requests. Labels:\n"
          + "\n".join(f"{k}: {v}" for k, v in DEFINITIONS.items())
          + "\nIf a message does not say which change is wanted, answer "
            "unclear. Reply with one line per message: the number, a "
            "space, and the label. Nothing else.")

NEIGHBOR = {
    "voluntary_rebook": "involuntary_rebook",
    "involuntary_rebook": "voluntary_rebook",
    "cancel_credit": "cancel_refund", "cancel_refund": "cancel_credit",
    "involuntary_refund": "cancel_refund",
    "accept_schedule": "involuntary_rebook",
    "hotel_cancel": "hotel_date_change",
    "hotel_date_change": "hotel_cancel",
    "ancillary_refund": "cancel_refund", "upgrade": "voluntary_rebook",
    "car_change": "voluntary_rebook", "name_correction": "upgrade",
}


def sim_teacher(msgs: list[Message], seed: int = 17,
                slip: float = 0.01) -> dict[str, str]:
    rng = seeded(seed, "adapt", "teacher")
    out = {}
    for m in msgs:
        if m.vague:
            out[m.msg_id] = UNCLEAR
        elif rng.random() < slip * (2 if m.short else 1) \
                and m.label in NEIGHBOR:
            out[m.msg_id] = NEIGHBOR[m.label]
        else:
            out[m.msg_id] = m.label
    return out


def prompt_for(batch: list[Message]) -> str:
    return "\n".join(f"{i + 1}. {m.text}" for i, m in enumerate(batch))


LINE = re.compile(r"^\s*(\d+)[.):]?\s+([a-z_]+)")


def parse(text: str, n: int) -> list[str]:
    got = {}
    for ln in text.splitlines():
        m = LINE.match(ln)
        if m and 1 <= int(m.group(1)) <= n:
            got[int(m.group(1))] = m.group(2)
    return [got.get(i + 1, "unparsed") for i in range(n)]


def client(role: str, meter: SpendMeter, offline: bool) -> ModelClient:
    if offline:
        return ModelClient(role, meter=meter,
                           transport=FixtureTransport(FIXTURES))
    return ModelClient(role, meter=meter, cache_dir=FIXTURES)


def label(msgs: list[Message], role: str, meter: SpendMeter,
          offline: bool | None = None) -> tuple[dict[str, str], dict]:
    """Labels for `msgs` from one role, ten to a call."""
    if offline is None:
        offline = os.environ.get("DESIGNLAB_OFFLINE") == "1" or \
            not os.environ.get("ANTHROPIC_API_KEY", "").strip()
    c = client(role, meter, offline)
    out: dict[str, str] = {}
    stats = {"calls": 0, "cached": 0, "cost": 0.0, "in": 0, "out": 0,
             "model": ""}
    for i in range(0, len(msgs), BATCH):
        batch = msgs[i:i + BATCH]
        r = c.complete(prompt_for(batch), system=SYSTEM,
                       max_tokens=MAX_TOKENS[role] * len(batch))
        stats["calls"] += 1
        stats["cached"] += int(r.cached)
        stats["cost"] += r.cost_usd
        stats["in"] += r.input_tokens
        stats["out"] += r.output_tokens
        stats["model"] = r.model
        for m, lab in zip(batch, parse(r.text, len(batch))):
            out[m.msg_id] = lab
    return out, stats


def live_sample(msgs: list[Message], n: int = 100, seed: int = 17,
                month: str | None = None) -> list[Message]:
    """First messages from the training months (or one month), seeded."""
    pool = [m for m in msgs if m.msg_id.endswith("-1") and
            (m.month == month if month else m.month < "2026-04")]
    label = "live" if month is None else f"live-{month}"
    return seeded(seed, "adapt", label).sample(pool, n)


def known(label: str) -> bool:
    return label in TYPES or label == UNCLEAR
