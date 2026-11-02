"""Figure 15.5  Escalation rate against confidence threshold.

Reading order: left to right along the curve as the threshold on the
small model's self-reported confidence rises from 0.5 to 0.99; the
verifier's point sits below the curve. Illustrative change-intent
cascade (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

pts = ((0.5, 0.0, 4.8), (0.8, 0.5, 4.6), (0.9, 3.0, 4.2), (0.95, 18.0, 3.0),
       (0.97, 35.0, 2.2), (0.99, 62.0, 1.4))
fig, ax = fl.figure(4.5, 3.4)
xs = [p[1] for p in pts]
ys = [p[2] for p in pts]
ax.plot(xs, ys, color=fl.C["model"], marker=fl.MARKERS[0], lw=fl.STROKE["data"])
for t, x, y in pts:
    if t in (0.5, 0.9, 0.95, 0.99):
        fl.label_line(ax, x, y, f"{t}", dy=-10 if t == 0.9 else 8, dx=4)
ax.plot([11], [1.1], marker=fl.MARKERS[1], ms=9, color=fl.C["verified"], ls="none")
fl.note(ax, (11, 1.1), (20, 0.4), "verifier: 11% escalated")
fl.note(ax, (1.0, 4.7), (12, 5.2), "below 0.9: almost nothing escalates")
ax.set_xlim(-2, 66)
ax.set_ylim(0, 5.8)
ax.set_xlabel("Steps escalated (%)")
ax.set_ylabel("Wrong answers kept (%)")
fl.save(fig)
