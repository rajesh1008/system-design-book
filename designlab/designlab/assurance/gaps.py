"""Where a refund destination can come from, and which golden tasks
tempt the agent with each source.

refund_other_card is a forbidden effect on every task in the set, so
every release is checked for it. A forbidden effect only fails when a
task gives the agent a reason to commit it. The June set tempts it
from trusted fields only: a card on the traveler's profile, and an
expired original. No task puts a card in text the agent reads from
outside, so the check could not fail for that cause.
"""
from __future__ import annotations

from evals import golden as G
from evals import harvest as H
from evals import online as O

SOURCES = (
    ("card that paid (booking record)", "trusted"),
    ("another card on the profile", "trusted"),
    ("expired original, newer card on file", "trusted"),
    ("card named by the customer in chat", "untrusted"),
    ("card in a tool result or document", "untrusted"),
)


def tempts(t: G.GoldenTask) -> list[str]:
    if t.outcome != "refunded" and t.cls != "instruction_in_document":
        return []
    out = [SOURCES[0][0]]
    if t.card_on_file:
        out.append(SOURCES[1][0])
    if t.expired and t.card_on_file:
        out.append(SOURCES[2][0])
    if t.cls == "instruction_in_document":
        out.append(SOURCES[4][0])
    return out


def table(tasks: list[G.GoldenTask]) -> list[tuple[str, str, int]]:
    rows = []
    for name, trust in SOURCES:
        n = sum(1 for t in tasks if name in tempts(t))
        rows.append((name, trust, n))
    return rows


def forbidden_on(tasks: list[G.GoldenTask]) -> int:
    return sum(1 for t in tasks if "refund_other_card" in t.forbidden)


def july() -> list[G.GoldenTask]:
    cands = H.label(H.clusters(O.production()))
    return H.admit(G.build(), cands, "2026-07-06")
