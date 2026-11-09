"""Figure 43.3  Telecom care: five gaps closed.

Reading order: one row per gap of Chapter 2's chain, top to bottom:
the answer the design gives and the owner who answers for it. All five
rows pass the linter, so all are drawn in green. From
designs/data/telecom-care.toml, section [gaps].
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("G1", "Typed credit or plan", "Care architect"),
        ("G2", "Line scope and amount", "Privacy counsel"),
        ("G3", "Key and order id", "Care architect"),
        ("G4", "Two reconcilers", "Billing operations"),
        ("G5", "Cost per contact", "Head of care"))
fig, ax = table(rows, ("Gap", "Answer", "Owner"), (0.0, 0.55, 3.0),
                toks=["verified"] * 5, h=3.0)
fl.save(fig)
