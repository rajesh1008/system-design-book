"""Figure 48.3  What runtimes will absorb.

Reading order: one row per piece of agent plumbing, top to bottom in
the order a managed runtime reached general availability. The middle
column is the date it was absorbed, or Lakeshore's dated bet; the
right column is what stays with the team either way. The last row,
the outcome check, does not move. From plan.core.runtimes on vendor
pages fetched November 9, 2026.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

from plan.core import runtimes  # noqa: E402

rows, toks = [], []
for r in runtimes():
    st = r["state"].replace("absorbed ", "").replace("bet by ", "bet ")
    rows.append((r["name"].capitalize(), st[:7] if st[0] == "2" else st[:8],
                 r["owned"].capitalize()))
    toks.append("model" if r["state"].startswith("absorbed") else "ops")
toks = ["ops" if t == "ops" else "evidence" for t in toks]
fig, ax = table(rows, ("Plumbing", "Absorbed", "Still yours"),
                (0.0, 1.65, 2.65), width=5.0, toks=toks, h=3.4)
fl.save(fig)
