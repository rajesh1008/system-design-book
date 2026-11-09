"""The twelve change types and the 1,200-case golden set (Chapter 27).

Volumes are Chapter 4's baseline year, in thousands of changes. Each
type has 100 cases in the golden set; what differs between types for
this chapter is how many legs a case touches and which specialists an
orchestrator-worker design would brief. Leg mixes are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded

# key: (label, volume in thousands, leg mix for 1, 2, 3, 4 legs,
#       specialists besides the per-leg searchers, searches per leg)
TYPES = {
    "voluntary-rebook": ("voluntary rebooking", 330,
                         (0.46, 0.34, 0.14, 0.06), ("rules", "notify"), 1),
    "cancel-for-credit": ("cancel for credit", 300,
                          (0.60, 0.33, 0.05, 0.02), ("rules", "notify"), 0),
    "involuntary-rebook": ("involuntary rebooking", 260,
                           (0.38, 0.32, 0.20, 0.10), ("rules", "notify"), 1),
    "hotel-cancel": ("hotel cancellation", 220,
                     (1.0, 0.0, 0.0, 0.0), ("hotel", "notify"), 0),
    "cancel-with-refund": ("cancel with refund", 210,
                           (0.58, 0.34, 0.06, 0.02),
                           ("rules", "refund", "notify"), 0),
    "involuntary-refund": ("involuntary refund", 190,
                           (0.50, 0.36, 0.10, 0.04),
                           ("rules", "refund", "notify"), 0),
    "upgrade": ("upgrade", 150,
                (0.55, 0.37, 0.06, 0.02), ("rules", "notify"), 0),
    "schedule-change-accept": ("accept schedule change", 130,
                               (0.40, 0.34, 0.18, 0.08),
                               ("rules", "notify"), 1),
    "hotel-date-change": ("hotel date change", 120,
                          (1.0, 0.0, 0.0, 0.0), ("hotel", "notify"), 0),
    "ancillary-refund": ("ancillary refund", 80,
                         (0.70, 0.27, 0.03, 0.0),
                         ("refund", "notify"), 0),
    "car-rental-change": ("car rental change", 60,
                          (1.0, 0.0, 0.0, 0.0), ("search", "notify"), 0),
    "name-correction": ("name correction", 50,
                        (0.62, 0.32, 0.05, 0.01), ("rules", "notify"), 0),
}
PER_TYPE = 100


@dataclass(frozen=True)
class Case:
    case_id: str
    kind: str
    legs: int


def label(kind: str) -> str:
    return TYPES[kind][0]


def golden_set(seed: int = 27) -> list[Case]:
    """100 cases per type; leg counts drawn from the type's mix."""
    cases = []
    for kind, (_, _, mix, _, _) in TYPES.items():
        rng = seeded(seed, "golden", kind)
        for i in range(PER_TYPE):
            legs = rng.choices((1, 2, 3, 4), weights=mix)[0]
            cases.append(Case(f"G27-{kind[:4].upper()}-{i:03d}", kind,
                              legs))
    return cases
