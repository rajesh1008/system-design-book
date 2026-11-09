"""Figure 42.4  The five gap questions.

Reading order: one row per gap of the evidence chain, G1 to G5, with
the short question and what points-transfer v1 answered on Thursday,
September 3, 2026, against v2 on Tuesday, September 8. From
review.gaps (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402
from review import gaps  # noqa: E402
from review.submission import load  # noqa: E402

short = ("What is proposed?", "Who permits it?", "Same retry; stop?",
         "Who verifies?", "Which number?")
v1 = [ok for _, _, ok, _ in gaps.walk(load("points-transfer-v1"))]
v2 = [ok for _, _, ok, _ in gaps.walk(load("points-transfer-v2"))]
rows = tuple((g[0], q, "yes" if a else "no", "yes" if b else "no")
             for g, q, a, b in zip(gaps.GAPS, short, v1, v2))
toks = ["verified" if b else "policy" for b in v2]
fig = table(rows, ("Gap", "Question", "v1", "v2"),
            (0.0, 0.55, 2.9, 3.8), toks=toks, h=3.0)
fl.save(fig)
