"""Figure 27.8  Success by task type, single against multi.

Reading order: one row per change type, ordered by volume. Hollow
circle: one agent; filled square: orchestrator-worker; verified
success over 300 runs a type (100 cases, three runs). Rows marked
with an asterisk are the three types orchestrator-worker won.
From topology.compare. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import figlib as fl  # noqa: E402

rows = (("Vol. rebook *", 83.3, 90.0),
        ("Credit cancel", 96.7, 94.0),
        ("Invol. rebook *", 81.3, 87.0),
        ("Hotel cancel", 97.0, 94.0),
        ("Refund cancel", 96.3, 91.3),
        ("Invol. refund", 95.7, 92.3),
        ("Upgrade", 96.3, 94.7),
        ("Sched. change *", 82.3, 91.3),
        ("Hotel dates", 96.3, 93.7),
        ("Ancillary", 97.0, 93.7),
        ("Car rental", 97.3, 92.3),
        ("Name fix", 97.0, 93.0))
fig, ax = fl.figure(4.5, 4.5)
n = len(rows)
for i, (name, s, o) in enumerate(rows):
    yy = n - 1 - i
    ax.plot([min(s, o), max(s, o)], [yy, yy], color=fl.GREY_LIGHT, lw=1.5, ls="-",
            zorder=1)
    ax.scatter(s, yy, s=36, facecolor="white", edgecolor=fl.C["model"],
               lw=1.5, zorder=2, marker="o")
    ax.scatter(o, yy, s=30, color=fl.C["ops"], zorder=3, marker="s")
ax.set_yticks(range(n))
ax.set_yticklabels([r[0] for r in reversed(rows)])
ax.set_xlim(78, 100)
ax.set_xlabel("Verified, % (circle one agent, square orch.)")
ax.grid(axis="x")
fl.save(fig)
