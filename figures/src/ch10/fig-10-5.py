"""Figure 10.5  The latency budget by plane.

Reading order: one row per plane, top to bottom, then the task line.
Each row gives the plane's p95 allowance and what the March design
replayed at. Values from python3 -m capacity.demo --part budget
(seed 10).
"""
import sys
from pathlib import Path

from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.traces import generate_traces  # noqa: E402
from capacity import budget as B  # noqa: E402

r = B.replay(generate_traces(10), B.MARCH)
names = {"knowledge": "Knowledge", "model": "Model",
         "queue": "Queue", "retries": "Retries",
         "tools": "Tools", "control": "Control",
         "trail": "Trail", "loop": "Loop"}
rows = [(names[p], B.PLANE_BUDGET[p], r.plane_p95[p]) for p in B.PLANES]
fig, ax = fl.figure(4.5, 3.9)
n = len(rows)
ax.set_xlim(0, 4)
ax.set_ylim(-1.4, n + 1)
ax.axis("off")
for x, h in ((0.95, "Plane"), (2.55, "Budget, s"), (3.45, "Replay, s")):
    ax.text(x, n + 0.45, h, ha="center", va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (name, bud, got) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.02, y + 0.1), 1.9, 0.8,
                           facecolor=fl.FILL["ops"], edgecolor=fl.C["ops"],
                           lw=0.75))
    ax.text(0.95, y + 0.5, name, ha="center", va="center", fontsize=9.5,
            color=fl.LABEL["ops"])
    ax.text(2.55, y + 0.5, f"{bud:g}", ha="center", va="center",
            fontsize=9.5)
    ax.text(3.45, y + 0.5, f"{got:.2f}", ha="center", va="center",
            color=fl.INK, **fl.mono(""))
ax.add_patch(Rectangle((0.02, -1.0), 3.96, 0.8,
                       facecolor=fl.FILL["verified"],
                       edgecolor=fl.INK, lw=2.5))
ax.text(0.95, -0.6, "Task", ha="center", va="center", fontsize=10,
        fontweight="bold", color=fl.LABEL["verified"])
ax.text(2.55, -0.6, f"{B.TASK_BUDGET_S:g}", ha="center", va="center",
        fontsize=10, fontweight="bold")
ax.text(3.45, -0.6, f"{r.p95:.1f}", ha="center", va="center",
        color=fl.INK, **fl.mono(""))
fl.save(fig)
