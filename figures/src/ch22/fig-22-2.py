"""Figure 22.2  Memory types and their stores.

Reading order: one row per type, from the shortest life to the
longest-lived record. Scopes from memory.record; ends from
memory.store and memory-retention-v1.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Short-term", "This conversation", "Session store;\nends with session"),
        ("Trip", "One itinerary's\nrequests", "Governed store;\nends with trip"),
        ("Standing", "Confirmed\npreferences", "Governed store;\n180 days, versioned"),
        ("Episodic", "What happened\nbefore", "Trail and cases;\ndesk reads"))
cols = (0.0, 1.25, 2.75)
heads = ("Type", "Holds", "Store and end")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, row in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL["knowledge"] if i % 2 == 0 else "white",
                           edgecolor=fl.C["knowledge"], lw=0.75))
    for x, t in zip(cols, row):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
