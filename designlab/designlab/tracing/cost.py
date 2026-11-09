"""Cost on every span, and cost per decision.

A chat span carries its own cost, priced from the pinned rates and
the token counts on the span. A decision is a span that commits the
run to something: a policy evaluation (refund or not), a decline sent
to the customer, or a hand-off to the desk. A decision costs the model
calls since the previous decision; the intake call serves every
decision in the run, so it is split across them by the share each one
already carries (largest remainder, to the micro-dollar).
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from cost.unit import attribute
from durable.bench import pct

from . import conventions as c
from .spans import Span

MICRO = Decimal("0.000001")


def is_decision(s: Span) -> str:
    if s.name.startswith("policy "):
        return "refund"
    if s.name == "execute_tool handoff_to_desk":
        return "handoff"
    return ""


def decisions(spans: list[Span], evidence: dict) -> list[dict]:
    """Decisions in the run, in order, each with its cost."""
    out, pending, intake = [], Decimal("0"), Decimal("0")
    for s in spans:
        if s.name.startswith("chat "):
            cost = Decimal(s.attrs[c.COST])
            if s.attrs.get(c.MODEL, "").startswith("claude-haiku"):
                intake += cost
            else:
                pending += cost
            continue
        kind = is_decision(s)
        if s.name == "execute_tool customer_notify":
            arg = evidence.get(s.span_id, {}).get("in", {})
            kind = "decline" if arg.get("kind") in ("decline",
                                                    "declined") else ""
            if not kind:
                continue
            if out and out[-1]["kind"] == "refund":
                out[-1]["own"] += pending   # the notice of a denial
                pending = Decimal("0")
                continue
        if kind:
            out.append({"kind": kind, "span": s.span_id, "own": pending})
            pending = Decimal("0")
    if out:
        out[-1]["own"] += pending        # the closing notice, if any
        weights = {str(i): int(d["own"] / MICRO) or 1
                   for i, d in enumerate(out)}
        shares = attribute(int(intake / MICRO), weights)
        for i, d in enumerate(out):
            d["usd"] = d["own"] + Decimal(shares[str(i)]) * MICRO
    return out


def stamp(spans: list[Span], evidence: dict) -> list[dict]:
    """Write each decision's cost onto its span."""
    ds = decisions(spans, evidence)
    by_id = {s.span_id: s for s in spans}
    for d in ds:
        by_id[d["span"]].attrs[c.DECISION_COST] = f"{d['usd']:.6f}"
    return ds


def by_span_kind(spans: list[Span]) -> dict[str, Decimal]:
    tot: dict[str, Decimal] = defaultdict(Decimal)
    for s in spans:
        if s.name.startswith("chat "):
            tot[s.attrs[c.MODEL]] += Decimal(s.attrs[c.COST])
    return dict(tot)


def distribution(results) -> dict[str, dict]:
    """p50, p95 and max cost per decision, by kind, over a fleet."""
    by: dict[str, list[float]] = defaultdict(list)
    for r in results:
        for d in decisions(r.trace, r.evidence):
            by[d["kind"]].append(float(d["usd"]))
            by["all"].append(float(d["usd"]))
    return {k: {"n": len(v), "p50": pct(v, 50), "p95": pct(v, 95),
                "max": max(v), "mean": sum(v) / len(v)}
            for k, v in by.items()}
