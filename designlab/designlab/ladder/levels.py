"""The seven levels of the ladder, and what each one tests.

A level is a rung of the question, not of the candidate. Each level
adds one thing to the design the level below it asked for, and every
level asks for the five gaps. The tiers used in chapter markup (mid,
senior, staff, principal) map onto the ladder by the highest level a
candidate at that tier is expected to clear; the bank (Chapter 47)
reads TIER_TOP to index questions by level.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Level:
    code: str
    name: str
    adds: str
    tests: str
    planes: tuple[str, ...]
    lead_gap: str
    bar: int          # rubric total (of 14) needed to clear the level


LEVELS: tuple[Level, ...] = (
    Level("L1", "one agent, one tool, one permission",
          "a single effect and its permission",
          "can you name the effect before the model",
          ("action", "control"), "G2", 8),
    Level("L2", "the agent acts on its own",
          "autonomy levels, limits, a person on the loop",
          "can you bound an effect nobody approves",
          ("action", "control"), "G2", 9),
    Level("L3", "retrieval and memory",
          "knowledge with an as-of date and provenance",
          "can you tell a fact from a remembered one",
          ("action", "control", "knowledge"), "G1", 10),
    Level("L4", "durability",
          "crashes, retries, and the backlog of a storm",
          "does a retry stay the same request",
          ("action", "control", "trail"), "G3", 10),
    Level("L5", "the control plane",
          "policy, gateway, identity, budgets, kill switch",
          "is permission outside every loop",
          ("action", "control", "trail"), "G2", 11),
    Level("L6", "security and evaluation",
          "an adversary in the input and a release gate",
          "what verifies, and what attacks the verifier",
          ("action", "control", "knowledge", "trail"), "G4", 12),
    Level("L7", "fifty use cases",
          "a platform, decision rights, and the operating model",
          "who owns each gap when fifty teams ship",
          ("action", "control", "knowledge", "trail"), "G5", 12),
)

BY_CODE = {lv.code: lv for lv in LEVELS}

# The highest level a candidate at each tier is expected to clear.
TIER_TOP = {"mid": "L3", "senior": "L5", "staff": "L6",
            "principal": "L7"}


def level(code: str) -> Level:
    return BY_CODE[code]


def tier_for(cleared: list[str]) -> str:
    """The tier whose top level is the highest level cleared in a row.

    A candidate clears levels from L1 upward; a level that fails stops
    the count, because a staff answer that misses the permission of
    level one is not a staff answer.
    """
    top = 0
    for i, lv in enumerate(LEVELS, start=1):
        if lv.code in cleared:
            top = i
        else:
            break
    best = "below mid"
    for tier, code in TIER_TOP.items():
        if top >= int(code[1:]):
            best = tier
    return best
