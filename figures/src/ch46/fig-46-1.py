"""Figure 46.1  The seven levels.

Reading order: one row per level, level one at the top: what the
level adds to the design and the rubric bar out of fourteen. The bar
rises with the level. From ladder.levels.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

from ladder.levels import LEVELS  # noqa: E402

short = {"L1": "One tool", "L2": "Acts alone",
         "L3": "Retrieval, memory", "L4": "Durability",
         "L5": "Control plane", "L6": "Security, evals",
         "L7": "Fifty use cases"}
rows = [(lv.code, short[lv.code], lv.lead_gap, str(lv.bar))
        for lv in LEVELS]
fig, ax = table(rows, ("Level", "Adds", "Gap", "Bar"),
                (0.0, 0.8, 3.55, 4.35), width=5.0,
                toks=["org"] * 7, h=3.2, fs=9)
fl.save(fig)
