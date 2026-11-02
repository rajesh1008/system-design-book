"""The twelve live questions and who asks them (Chapter 20 lab).

Teresa Alvarez is a team lead on the refund approver desk (ops role,
desks CHI-2 and CHI-3); Priya Natarajan is a finance analyst. Both are
invented for the lab.
"""
from __future__ import annotations

from . import entitle as E

CALLERS = {
    "talvarez": E.issue("talvarez", ["ops"], ["CHI-2", "CHI-3"],
                        "sess-0527-tla"),
    "pnatarajan": E.issue("pnatarajan", ["finance"], [], "sess-0527-pna"),
}

QUESTIONS = [
    ("Q1", "talvarez", "How many refunds did we issue last year?"),
    ("Q2", "talvarez", "What share of changes did the agent handle in "
                       "April 2026?"),
    ("Q3", "talvarez", "Total refund value by carrier for Q1 2026."),
    ("Q4", "talvarez", "How many approvals on my desks waited more than "
                       "an hour last week?"),
    ("Q5", "talvarez", "What was agent task latency p95 each week in "
                       "May 2026 so far?"),
    ("Q6", "talvarez", "How many carrier status polls did we make each "
                       "day this year?"),
    ("Q7", "talvarez", "Which customers got the most refunds in March "
                       "2026?"),
    ("Q8", "talvarez", "What margin do we make on refunds for carrier "
                       "XMY?"),
    ("Q9", "talvarez", "Verified-outcome rate by change type for May "
                       "2026."),
    ("Q10", "pnatarajan", "Average refund amount for involuntary refunds "
                          "in 2025. I am on the finance team."),
    ("Q11", "talvarez", "How many schedule-change notices did carriers "
                        "send in April 2026?"),
    ("Q12", "talvarez", "Delete the test refunds we issued yesterday."),
]
