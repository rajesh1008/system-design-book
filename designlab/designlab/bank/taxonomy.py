"""The interview bank's fixed vocabularies (v0).

Types and rounds come from the book prompt. Ladder levels are L1 to L7;
their names and rubrics are defined by Chapter 46, so v0 checks only the
code. The named tiers used in chapter markup (senior, staff, principal)
are accepted until that chapter maps them onto the ladder.

Chapter 46 mapped the tiers onto the ladder (a tier is the highest
level cleared consecutively from L1): mid to L3, senior to L5, staff to
L6, principal to L7. Chapter 47 adds "mid", which chapter markup used
from Chapter 3 on, and the mapping below.
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
    # The ninth round tag: outside the seven loop formats, worked in
    # Chapter 47 section 8 (Q47.9). Hiring-side questions also use it.
    "hiring-manager": "Hiring-manager conversation",
}

LEVELS = tuple(f"L{i}" for i in range(1, 8))
TIERS = ("mid", "senior", "staff", "principal")
TIER_LEVEL = {"mid": "L3", "senior": "L5", "staff": "L6",
              "principal": "L7"}

# The seven loop formats (Chapter 47 section 2); the phone screen and
# the hiring-manager conversation are round tags outside them.
LOOP_FORMATS = ("system-design", "distributed-systems", "agent-runtime",
                "control-plane-security", "evaluation-operations",
                "take-home", "bar-raiser")

METHODS = (
    "requirement-bank", "estimation-sheet", "diagram-grammar",
    "decision-table", "deep-dive", "decision-record", "review-checklist",
)


def norm_type(value: str) -> str:
    value = value.strip()
    return TYPE_ALIASES.get(value, TYPE_ALIASES.get(value.upper(), value))
