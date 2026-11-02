"""Figure 18.4  Lever sensitivity.

Reading order: one bar per lever, cost per verified outcome from the
better to the worse setting around May's value. The bottom bar is the
hand-off rate, which is not on the token bill. From cost.demo --part
levers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from cost.levers import handoff_lever, sensitivity  # noqa: E402

rows = sensitivity()
base = rows[0]["outcome_base"]
bars = [(r["lever"].capitalize(), r["outcome_better"], r["outcome_worse"])
        for r in rows]
h = dict(handoff_lever())
bars.append(("Hand-offs 6-18%", h[0.06], h[0.18]))
fig, ax = fl.figure(4.5, 3.2)
for i, (label, lo, hi) in enumerate(bars):
    y = len(bars) - 1 - i
    ax.barh(y, hi - lo, left=lo, height=0.55, color=fl.FILL["ops"],
            edgecolor=fl.C["ops"], lw=0.75,
            hatch="///" if label.startswith("Hand") else None)
    ax.text(hi + 0.01, y, f"${lo:.2f}-{hi:.2f}", va="center",
            fontsize=9.5, color=fl.INK)
ax.axvline(base, color=fl.INK, lw=1.0)
ax.text(base + 0.005, len(bars) - 0.35, f"May ${base:.2f}", fontsize=9.5,
        color=fl.INK)
ax.set_yticks(range(len(bars)))
ax.set_yticklabels([b[0] for b in reversed(bars)], fontsize=9.5)
ax.set_xlim(1.55, 2.3)
ax.set_ylim(-0.6, len(bars) - 0.1)
ax.set_xlabel("Dollars per verified outcome")
fl.save(fig)
