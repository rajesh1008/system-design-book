"""Figure 38.1  Cost per verified outcome by kind of change.

Reading order: one pair of bars per kind of change, top to bottom; the
upper bar is July as closed, the lower is August. The shaded strip is
August's forecast band. From economics.outcome (Lakeshore figures are
illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from economics import outcome  # noqa: E402

jul, aug = outcome.kinds("July"), outcome.kinds("August")
names = list(jul)
lo, _mid, hi = outcome.BAND["August"]
fig, ax = fl.figure(4.5, 3.0)
ax.axvspan(lo, hi, color=fl.FILL["knowledge"], lw=0)
ax.text(lo + 0.01, len(names) - 0.35, "August band", fontsize=9,
        color=fl.INK)
for i, n in enumerate(names):
    y = len(names) - 1 - i
    for dy, v, tok, hatch in ((0.18, jul[n], "fail", ""),
                              (-0.18, aug[n], "verified", "///")):
        ax.barh(y + dy, v, height=0.32, color=fl.FILL[tok],
                edgecolor=fl.C[tok], lw=0.9, hatch=hatch)
        ax.text(v + 0.02, y + dy, f"${v:.2f}", va="center", fontsize=9,
                color=fl.INK)
ax.set_yticks(range(len(names)))
ax.set_yticklabels([n.capitalize() for n in reversed(names)])
ax.set_xlim(0, 2.6)
ax.set_ylim(-0.6, len(names) - 0.1)
ax.set_xlabel("Dollars per verified outcome (upper July, lower August)")
fl.save(fig)
