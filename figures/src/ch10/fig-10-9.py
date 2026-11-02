"""Figure 10.9  Utilization against wait.

Reading order: left to right. Kingman's mean wait for one server with
1.04 s calls and Poisson arrivals; markers at the limit Lakeshore
bought (68% used) and at 95%. From capacity.queue, seed 10 fit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from capacity.queue import kingman  # noqa: E402

S = 1.04
rho = [i / 1000 for i in range(200, 976, 5)]
w = [kingman(r, S) for r in rho]
fig, ax = fl.figure(4.5, 3.4)
ax.plot([100 * r for r in rho], w, color=fl.C["model"], lw=1.5, marker="")
for r, txt, off in ((0.68, "bought: 68%", (40, 9)),
                    (0.95, "motorway: 95%", (68, 30))):
    ax.plot([100 * r], [kingman(r, S)], marker="o", color=fl.INK, ms=5)
    if r > 0.9:
        fl.note(ax, (95, kingman(r, S)), off, f"{txt}, {kingman(r, S):.1f} s")
    else:
        ax.text(off[0], off[1] - 6.3, f"{txt}, {kingman(r, S):.1f} s",
                fontsize=9.5, color=fl.INK)
ax.set_xlim(20, 100)
ax.set_ylim(0, 42)
ax.set_xlabel("Utilization (%)")
ax.set_ylabel("Mean wait a call (s)")
fl.save(fig)
