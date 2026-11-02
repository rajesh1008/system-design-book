"""Slots: the parts of a model call, in the order the assembler lays
them out, with the cap each one may use.

The stable slots take their sizes from the Chapter 14 serving trace, so
the two labs describe the same prompt. A slot's cap is a share of the
per-step budget the team has agreed to, not a guess at the window.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from serving.trace import EXAMPLES, POLICY, SYSTEM, TIMESTAMP_TOKENS, TOOLS

assert SYSTEM == ("instructions-v7", 1_100)   # the same file as Chapter 14

# Stable to volatile. A slot later in this list changes more often.
ORDER = ("tools", "instructions", "policy", "examples",   # per release
         "task", "memory", "history",                      # per task
         "retrieved", "pinned", "clock")                   # per step
STABLE = ("tools", "instructions", "policy", "examples")

BUDGET = 48_000          # tokens a step, set below the knee (60,000)
COMPACT_AT = 0.70        # compact when a step would pass 33,600
WINDOW = 200_000         # the pinned model's window [VERIFY in prose]

# Caps in tokens. History has none of its own: it gets what is left,
# and compaction keeps it from taking the rest.
# The instruction cap is the v7 file (1,100) plus room for one release;
# the retrieved cap is three passages of the usual size.
CAPS = {"tools": 1_500, "instructions": 1_200, "policy": 1_200,
        "examples": 800, "task": 4_000, "memory": 1_000,
        "retrieved": 2_000, "pinned": 600, "clock": 32}
INSTRUCTIONS = {"v7": ("instructions-v7", 1_100),     # Chapter 14
                "v8": ("instructions-v8", 1_460),
                "v9": ("instructions-v9", 1_180)}


@dataclass(frozen=True)
class Item:
    slot: str
    key: str
    tokens: int
    rank: int = 0            # lower is kept first when a slot is cut
    text: str = ""


@dataclass
class Budget:
    per_step: int = BUDGET
    compact_at: float = COMPACT_AT
    caps: dict = field(default_factory=lambda: dict(CAPS))

    @property
    def trigger(self) -> int:
        return int(self.per_step * self.compact_at)


def stable_items(kind: str = "rebook", release: str = "v7") -> list[Item]:
    """The release-stable part of every call. Tools, policy, and examples
    are the Chapter 14 sizes; the instruction file is the named release
    (v7 is the Chapter 14 file)."""
    key, size = INSTRUCTIONS[release]
    return [Item("tools", TOOLS[0], TOOLS[1]),
            Item("instructions", key, size),
            Item("policy", POLICY[kind][0], POLICY[kind][1]),
            Item("examples", EXAMPLES[0], EXAMPLES[1])]


def clock_item(stamp: str) -> Item:
    return Item("clock", f"ts:{stamp}", TIMESTAMP_TOKENS)
