"""The durability card and the numbers behind it.

The lab computes the kill-suite rate and a local replay time. The
production replay figures are Ben Carter's March 2026 benchmark on
2,000 trajectories from the phase-2 journal (Lakeshore fact, ch09).
"""
from __future__ import annotations

BEN_REPLAY_S = {"runs": 2000, "p50": 0.61, "p90": 1.32, "p99": 2.4,
                "max": 2.9, "target": 3.0,
                "measured": "March 27, 2026", "who": "Ben Carter"}

CARD = [  # (measure, value, target, source)
    ("Resume rate after a kill at any step", "100%", "100%",
     "kill suite, 24 kill points"),
    ("Replay of any run, p99", "2.4 s", "under 3 s",
     "replay benchmark, 2,000 runs"),
    ("Waits outstanding without a timer", "0", "0",
     "timer table against open requests"),
    ("Approvals re-filed by a restart", "0", "0",
     "desk requests per run"),
]

ENGINES = [  # option, then five cells
    ("Engine",
     ["yes", "yes", "yes", "yes", "keys"]),
    ("Checkpointer\nand database",
     ["yes", "in state", "in state", "no", "keys"]),
    ("Run store\n(March)",
     ["yes", "yes", "yes", "yes", "keys"]),
    ("Checkpointer\n(February)",
     ["yes", "no", "no", "no", "no"]),
    ("Pilot loop",
     ["no", "no", "no", "no", "no"]),
]
ENGINE_COLS = ["Position", "Outputs", "Approval", "Timers", "Once"]
