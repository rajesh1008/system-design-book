"""Figure 20.10  The knowledge card, as of May 31, 2026.

Reading order: top to bottom. Four numbers from the plane: the metrics
in the layer, the share of queries estimated before they ran, the share
refused on cost, and answered queries outside entitlement in Owen
Fletcher's review of May 29 (Lakeshore figures are illustrative).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Metrics in the layer", "41", "knowledge"),
        ("Queries estimated first", "100%", "verified"),
        ("Refused on cost", "3% (42 of 1,436)", "policy"),
        ("Outside entitlement", "0", "verified")]

fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(0, 6.4)
ax.set_ylim(0, len(rows) + 0.2)
ax.axis("off")
for i, (name, val, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.add_patch(Rectangle((0.05, y + 0.1), 6.3, 0.8,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.8))
    ax.text(0.2, y + 0.5, name, ha="left", va="center", fontsize=10)
    ax.text(6.2, y + 0.5, val, ha="right", va="center", fontsize=11,
            color=fl.LABEL[tok], fontweight="bold")
fl.save(fig)
