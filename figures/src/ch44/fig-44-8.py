"""Figure 44.8  What changed: three designs.

Reading order: one row per decision record from the review of Monday,
September 21, 2026, top to bottom: the record, the change it makes,
who owns and who signs it, and when it reverses. From
golive.review.DESIGNS (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("R-RBK-1", "Departure order", "Marcus", "Misses rise"),
        ("R-RFD-1", "Surge rule, $500", "Rachel", "Error > 0.5%"),
        ("R-PLT-1", "Storm reserve", "Sarah", "Undeclared use"))
toks = ["ops", "policy", "verified"]
fig, ax = table(rows, ("Record", "Change", "Signs", "Reverse if"),
                (0.0, 1.0, 2.75, 3.65), width=5.0, toks=toks, h=3.0,
                fs=9)
fl.save(fig)
