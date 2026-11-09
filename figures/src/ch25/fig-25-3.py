"""Figure 25.3  Loop shapes and when each fits.

Reading order: one row per shape, from the most constrained to the most
open, with what each fits and the stops it needs beyond the harness's
own. The highlighted row is the shape Lakeshore chose for refunds, a
known and fixed path.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("State machine", "Known, fixed steps", "Legal transitions"),
        ("Plan and execute", "Known, variable steps", "Checked plan"),
        ("ReAct", "Open-ended", "Step budget"),
        ("Reflection", "A verifier exists", "Retry cap"),
        ("Bounded search", "High value, verifier", "Branch budget")]
hi = 0

fig, ax = fl.figure(5.4, 3.6)
ax.set_xlim(0, 8.0)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Shape"), (2.55, "Fits"), (5.55, "Also needs")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=10,
            fontweight="bold")
for i, (name, fits, stop) in enumerate(rows):
    y = len(rows) - 1 - i
    tok = "verified" if i == hi else "model"
    ax.add_patch(Rectangle((2.45, y + 0.1), 2.95, 0.8, facecolor="white",
                           edgecolor=fl.C[tok], lw=1.8 if i == hi else 0.6))
    ax.add_patch(Rectangle((5.45, y + 0.1), 2.5, 0.8,
                           facecolor=fl.FILL["policy"], edgecolor=fl.C["policy"],
                           lw=1.8 if i == hi else 0.6))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=10,
            fontweight="bold" if i == hi else "normal")
    ax.text(2.55, y + 0.5, fits, ha="left", va="center", fontsize=10,
            color=fl.INK)
    ax.text(5.55, y + 0.5, stop, ha="left", va="center", fontsize=10,
            color=fl.INK)
fl.save(fig)
