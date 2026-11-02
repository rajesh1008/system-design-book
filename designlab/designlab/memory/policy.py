"""Who may read what the agent wrote, and what a memory may not do.

READ_POLICY is by role. The agent loop reads preferences for its own
tenant and never health or consent notes; the agent desk and the
privacy office read everything for the case in front of them,
superseded versions included; analytics reads no record at all, only
the audit's counts.

`authorize` stands in front of the control plane. A proposal's grounds
are listed as "fact:<name>" (a knowledge-plane Fact read from a system
of record) or "memory:<id>". If any ground is a memory, or a fact whose
source is the memory store, the proposal is not decided by policy; it
is escalated to a person with the reason written to the trail, so a
remembered promise is checked against the record it claims to be.
"""
from __future__ import annotations

from planes.control import Decision

SENSITIVE = ("health", "consent")
MEMORY_RECEIVER = "agent desk"     # a person checks the record itself
READ_POLICY = {
    "agent-loop": {"subjects": "all-but-sensitive", "history": False},
    "agent-desk": {"subjects": "all", "history": True},
    "privacy-office": {"subjects": "all", "history": True},
    "analytics": {"subjects": "none", "history": False},
}


def can_read(role: str, record) -> bool:
    rule = READ_POLICY.get(role)
    if rule is None or rule["subjects"] == "none":
        return False
    if rule["subjects"] == "all-but-sensitive":
        return record.subject not in SENSITIVE
    return True


def can_read_history(role: str) -> bool:
    return READ_POLICY.get(role, {}).get("history", False)


def grounds_problems(context, grounds: list[str]) -> list[str]:
    """Reasons these grounds cannot carry a permission (empty if fine)."""
    out = []
    for g in grounds:
        kind, _, ref = g.partition(":")
        if kind == "memory":
            out.append(f"grounds cite memory {ref}")
        elif kind == "fact":
            f = context.facts.get(ref)
            if f is None:
                out.append(f"fact {ref} not in the packet")
            elif str(f.source).startswith("memory"):
                out.append(f"fact {ref} from {f.source}")
        else:
            out.append(f"unknown ground {g}")
    return out


def authorize(control, proposal, context, grounds: list[str]) -> Decision:
    """Control decides only on grounds that are not memory."""
    problems = grounds_problems(context, grounds)
    if not problems:
        return control.decide(proposal, context)
    row = control.autonomy.row(proposal.action)
    d = Decision("escalate", proposal.action, row.level,
                 "memory is not authority: " + "; ".join(problems),
                 handoff="async", receiver=MEMORY_RECEIVER)
    d.pending_id = f"APR-{len(control.pending) + 1:05d}"
    control.pending[d.pending_id] = (proposal, d)
    control.trail.decision(d, proposal)
    return d
