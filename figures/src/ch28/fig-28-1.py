"""Figure 28.1  Unattended against requested work.

Reading order: one row per property, top to bottom; the requested
column on the left, the unattended column on the right. The seven
rows are the seven properties of loops.lint.PROPS.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Trigger", "Request", "Schedule, event"),
        ("Stop", "Person satisfied", "Machine check"),
        ("State", "Conversation", "Run store"),
        ("Verify", "Person", "Separate verifier"),
        ("Budget", "Task", "Loop day"),
        ("Change", "Person's case", "Named scope"),
        ("Human", "In the loop", "On the loop"))
cols = (0.0, 1.35, 2.95)
heads = ("Property", "Requested", "Unattended")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (prop, req, un) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 1.3, 0.88,
                           facecolor=fl.FILL["knowledge"],
                           edgecolor=fl.C["knowledge"], lw=0.75))
    ax.add_patch(Rectangle((1.35, y + 0.06), 1.55, 0.88,
                           facecolor=fl.FILL["org"],
                           edgecolor=fl.C["org"], lw=0.75))
    ax.add_patch(Rectangle((2.95, y + 0.06), 1.65, 0.88,
                           facecolor=fl.FILL["ops"],
                           edgecolor=fl.C["ops"], lw=1.25))
    for x, t in zip(cols, (prop, req, un)):
        ax.text(x + 0.07, y + 0.5, t, va="center", fontsize=9.5,
                color=fl.INK, fontweight="bold" if x == cols[2] else None)
fl.save(fig)
