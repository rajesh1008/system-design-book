"""Route each question to one of the nine round tags (Chapter 47).

The chapters tagged almost every question `system-design`, because
each was written as a design question for that chapter's material.
A loop needs more: a control-plane round wants the control-plane
questions from every Part. `route` keeps any tag a chapter declared
other than `system-design`, and otherwise reads the question's heading
and type with an ordered list of rules, first match wins, and falls
back on the chapter's Part. Every routed question records the rule
that placed it, so a reader can audit any placement. It is a reading
aid for building loops and for Appendix J, not a judgment about the
question; a chapter that declares a tag always wins.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import Question

# Ordered: the first rule whose words appear in the heading wins.
WORDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("take-home", "writes a document", (
        "decision record", "write a ", "write the ", "write down",
        "one page", "one-page", "document", "the record")),
    ("control-plane-security", "names a control", (
        "permission", "policy", "polic", "inject", "attack", "threat",
        "identity", "credential", "token", "kill switch", "approv",
        "authoriz", "egress", "exfiltrat", "privilege", "security",
        "tenant", "isolat", "secret", "pii", "regulat", "audit")),
    ("evaluation-operations", "names an operation", (
        "eval", "golden", "judge", "regression", "canary", "rollback",
        "roll back", "release", "on-call", "incident", "error budget",
        "service objective", "slo", "trace", "observab", "monitor",
        "drift", "recover", "bill", "spend", "cost", "runbook",
        "alert", "measure", "verified outcome", "go-live", "storm")),
    ("agent-runtime", "names the runtime", (
        "harness", "loop", "tool", "runtime", "sdk", "skill",
        "instruction file", "context", "compaction", "sub-agent",
        "topology", "orchestrat", "memory", "trigger", "sandbox",
        "coding agent", "handoff", "hand-off", "multi-agent")),
    ("distributed-systems", "names a distributed fault", (
        "idempot", "retry", "retries", "exactly once", "exactly-once",
        "queue", "backpressure", "durable", "checkpoint", "replay",
        "crash", "timeout", "time out", "capacity", "latency", "p95",
        "concurren", "throughput", "fan-out", "ordering", "partition",
        "duplicate", "twice", "workflow engine")),
)
PART_FALLBACK = {
    **{c: "distributed-systems" for c in range(7, 13)},
    **{c: "agent-runtime" for c in range(25, 31)},
    **{c: "control-plane-security" for c in range(31, 34)},
    **{c: "evaluation-operations" for c in range(34, 40)},
}
BAR_RAISER_WORDS = ("argue", "push back", "disagree", "decline",
                    "convince", "defend")


@dataclass(frozen=True)
class Routed:
    tag: str
    rule: str


def hiring_side(q: Question) -> bool:
    """Asked from the interviewer's side of the table."""
    text = q.text.lower()
    return (q.round == "hiring-manager" or "hiring side" in text
            or "hiring-side" in text)


def route(q: Question) -> Routed:
    if q.round and q.round != "system-design":
        return Routed(q.round, "declared")
    text = q.text.lower()
    if hiring_side(q):
        return Routed("hiring-manager", "hiring side")
    if q.type == "stakeholder" or any(w in text
                                      for w in BAR_RAISER_WORDS):
        return Routed("bar-raiser", "a person to convince")
    if q.type == "concept" and q.level == "mid":
        return Routed("phone-screen", "concept at mid")
    for tag, rule, words in WORDS:
        if any(w in text for w in words):
            return Routed(tag, rule)
    if q.chapter in PART_FALLBACK:
        return Routed(PART_FALLBACK[q.chapter], "the chapter's Part")
    return Routed("system-design", "whiteboard design")
