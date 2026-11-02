"""Figure 16.9  The contract scorecard.

Reading order: one row per number. Values as of May 31, 2026, over the
effect-tool calls from May 18 to 31, from the gateway intake count and
the trail. The highlighted row is the one the chapter turns on
(Lakeshore figures are illustrative).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Effect-tool calls checked", "38,412"),
        ("Schema-valid", "100%"),
        ("World-rejected", "2.1%"),
        ("Repaired within two tries", "94%"),
        ("Handed to the agent desk", "6%"),
        ("Rejected calls that reached a tool", "0")]
hi = len(rows) - 1

fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Number"), (4.35, "Value")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, val) in enumerate(rows):
    y = len(rows) - 1 - i
    tok = "verified" if i == hi else "ops"
    ax.add_patch(Rectangle((4.25, y + 0.12), 2.0, 0.76,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.8 if i == hi else 0.6))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5,
            fontweight="bold" if i == hi else "normal")
    ax.text(4.35, y + 0.5, val, ha="left", va="center", fontsize=9.5,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
