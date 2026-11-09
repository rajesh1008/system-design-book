"""Figure 47.1  What the loops test.

Reading order: one row per thing an agentic design loop tests, top to
bottom from framing to judgment, with the round that listens for it. The amber row is permission, the one
the opening page turns on and the postings name least.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = [("Framing the effects", "System design"),
        ("Partial failure", "Distributed"),
        ("The loop's bounds", "Harness"),
        ("Permission outside", "Control"),
        ("Verifying change", "Eval and ops"),
        ("Judgment with people", "Take-home, people")]
toks = ["org"] * 3 + ["policy"] + ["org"] * 2
fig, ax = table(rows, ("Tested", "Round"),
                (0.0, 2.3), width=5.0, toks=toks, h=3.0)
fl.save(fig)
