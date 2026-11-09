"""Figure 46.10  The rubric.

Reading order: one row per criterion, top to bottom: what earns the
full two points. The gaps row, in green, is the row an answer must
max to clear any level. From ladder.rubric.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

from ladder.rubric import CRITERIA  # noqa: E402

two = {"framing": "Effect and owner by minute 5",
       "estimation": "Number from a source",
       "chain": "Gate before effect",
       "gaps": "All five closed",
       "tradeoffs": "Two options, why not",
       "cost": "Per verified outcome",
       "communication": "Marks met, record"}
rows = [(c.capitalize(), two[c]) for c in CRITERIA]
toks = ["verified" if c == "gaps" else "org" for c in CRITERIA]
fig, ax = table(rows, ("Criterion", "Two points"), (0.0, 1.75),
                width=5.0, toks=toks, h=3.2, fs=9)
fl.save(fig)
