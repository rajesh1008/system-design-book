"""Figure 38.2  Where the cost of a verified outcome goes, July.

Reading order: Chapter 18's seven
driver lines, then the storm pooled under finance's May rule, then
INC-5's rework, one bar each, top to bottom. The model tokens are the
smallest line of all. From economics.outcome (Lakeshore
figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from economics import outcome  # noqa: E402

d = outcome.drivers("July")
c = outcome.close("July")
parts = [(k, v / d["verified"]) for k, v in d["lines"].items()]
parts += [("storm (pooled)", c.pooled), ("INC-5 rework", c.rework)]
toks = ["model", "ops", "ops", "evidence", "org", "org", "org",
        "fail", "fail"]
fig, ax = fl.figure(4.5, 3.4)
n = len(parts)
for i, ((name, v), tok) in enumerate(zip(parts, toks)):
    y = n - 1 - i
    ax.barh(y, v, height=0.62, color=fl.FILL[tok], edgecolor=fl.C[tok],
            lw=0.9, hatch="///" if name.startswith("storm") else "")
    ax.text(v + 0.01, y, f"${v:.3f}", va="center", fontsize=9,
            color=fl.INK)
ax.set_yticks(range(n))
ax.set_yticklabels([p[0][0].upper() + p[0][1:] for p in reversed(parts)])
ax.set_xlim(0, 0.8)
ax.set_xlabel(f"Dollars per verified outcome; July total ${c.total:.2f}")
fl.save(fig)
