"""The interview bank's fixed vocabularies (v0).

Types and rounds come from the book prompt. Ladder levels are L1 to L7;
their names and rubrics are defined by Chapter 46, so v0 checks only the
code. The named tiers used in chapter markup (senior, staff, principal)
are accepted until that chapter maps them onto the ladder.
"""

TYPES = {
    "concept": "C",
    "scenario": "S",
    "design": "T",          # technical design
    "stakeholder": "K",
}
TYPE_ALIASES = {"C": "concept", "S": "scenario", "T": "design",
                "K": "stakeholder", "technical-design": "design"}

ROUNDS = {
    "phone-screen": "Phone screen",
    "system-design": "System design whiteboard (45 minutes)",
    "distributed-systems": "Distributed-systems deep dive",
    "agent-runtime": "Agent runtime and harness design",
    "control-plane-security": "Control-plane and security review",
    "evaluation-operations": "Evaluation and operations scenario",
    "take-home": "Take-home architecture document",
    "bar-raiser": "Bar-raiser conversation",
    # Used by the Interview Voice Reference for hiring-side questions.
    "hiring-manager": "Hiring-manager conversation",
}

LEVELS = tuple(f"L{i}" for i in range(1, 8))
TIERS = ("senior", "staff", "principal")

METHODS = (
    "requirement-bank", "estimation-sheet", "diagram-grammar",
    "decision-table", "deep-dive", "decision-record", "review-checklist",
)


def norm_type(value: str) -> str:
    value = value.strip()
    return TYPE_ALIASES.get(value, TYPE_ALIASES.get(value.upper(), value))
