"""Figure 34.8  Releases blocked and why.

Reading order: one row per June release, top to bottom by date
(the release number carries the date): the release, the kind of change, the gate's verdict and
the reason. From evals.demo --part gate. Lakeshore figures are
illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("R-0602", "Memory", "Pass", ""),
        ("R-0603", "Model", "Pass", ""),
        ("R-0605", "Context", "Pass", ""),
        ("R-0609", "Tool server", "Blocked", "Wrong card"),
        ("R-0612", "Tool server", "Pass", ""),
        ("R-0617", "Model", "Blocked", "Reason flips"),
        ("R-0619", "Tool server", "Pass", ""),
        ("R-0621", "Identity", "Pass", ""),
        ("R-0623", "Knowledge", "Pass", ""))
cols = (0.0, 0.95, 2.15, 3.15)
heads = ("Release", "Change", "Gate", "Why")
fig, ax = fl.figure(4.5, 3.4)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, r in enumerate(rows):
    y = n - 1 - i
    tok = "fail" if r[2] == "Blocked" else "verified"
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "fail" else 0.75))
    for j, (x, v) in enumerate(zip(cols, r)):
        ax.text(x + 0.05, y + 0.5, v, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if j == 2 else None)
fl.save(fig)
