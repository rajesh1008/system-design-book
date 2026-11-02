"""Figure 11.9  The isolation scorecard.

Reading order: one row per number, each with its value; a tick means
the value meets the line set for it. Values as
of March 31, 2026, from the isolation suite, the egress log, and the
blast-radius probe (Lakeshore figures are illustrative).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Sandbox per session", "yes"),
        ("Shared writable paths", "0"),
        ("Cross-session reads", "0 in 10,000"),
        ("Egress hosts", "11"),
        ("Unlisted calls allowed", "0"),
        ("Caches keyed by tenant", "3 of 3"),
        ("Blast radius", "1 itinerary")]

fig, ax = fl.figure(4.5, 3.4)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 1)
ax.axis("off")
for x, h in ((0.05, "Number"), (3.65, "Value")):
    ax.text(x, len(rows) + 0.45, h, ha="left", va="center", fontsize=9.5,
            fontweight="bold")
for i, (name, val) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.add_patch(Rectangle((3.55, y + 0.12), 2.6, 0.76,
                           facecolor=fl.FILL["verified"],
                           edgecolor=fl.C["verified"], lw=0.75))
    ax.text(0.05, y + 0.5, name, ha="left", va="center", fontsize=9.5)
    ax.text(3.65, y + 0.5, "\u2713 " + val, ha="left", va="center",
            fontsize=9.5, color=fl.LABEL["verified"], fontweight="bold")
fl.save(fig)
