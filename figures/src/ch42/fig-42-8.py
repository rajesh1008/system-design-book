"""Figure 42.8  The review card.

Reading order: one row per line of the card Owen Fletcher's team
filed on Tuesday, September 8, 2026, for the log from November 2025.
The kill-switch row is highlighted. From review.log
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402
from review.log import card, load_log  # noqa: E402

c = card(load_log())
keys = (("Designs reviewed", "designs reviewed"),
        ("Declined", "declined"),
        ("Changed", "changed"),
        ("Approved as submitted", "approved as submitted"),
        ("Shipped, no kill switch", "shipped without a kill switch"),
        ("Records; revisited", None))
rows = []
for label, k in keys:
    v = (f"{c['records']}; {c['records revisited']}" if k is None
         else str(c[k]))
    rows.append((label, v))
toks = ["org"] * 4 + ["verified", "org"]
fig = table(tuple(rows), ("Line", "Value"), (0.0, 2.9), toks=toks,
            h=3.0)
fl.save(fig)
