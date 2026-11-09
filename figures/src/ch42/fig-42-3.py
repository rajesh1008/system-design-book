"""Figure 42.3  The production checklist by plane.

Reading order: four rows, one per plane, each with its four items in
short form, split by what a failure does. A shape item needs a new
box or arrow to fix and declines a design; a value item changes it. From
review.checklist (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("Action", "Gateway, stop", "Same key, pinned"),
        ("Control", "Outside the loop", "Policy, tier one, key"),
        ("Knowledge", "None", "Source, age, owner"),
        ("Trail", "Non-actor, own source", "Result, record"))
fig = table(rows, ("Plane", "Shape: decline", "Value: change"),
            (0.0, 1.05, 2.75),
            toks=["ops", "policy", "knowledge", "evidence"], h=3.0)
fl.save(fig)
