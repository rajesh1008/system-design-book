"""Figure 46.2  The clock.

Reading order: left to right across forty-five minutes. The top band
is the clock: four marks at 5, 15, 30, and 45 minutes. The lower band
is the answer from the opening, which spent minutes 3 to 31 on the
model, hatched red, and drew the chain at minute 31. From ladder.clock
and the A03b note.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from ladder import clock  # noqa: E402

fig, ax = fl.figure(4.5, 3.0)
ax.set_xlim(-0.5, 46)
ax.set_ylim(-0.4, 3.5)
ax.axis("off")
start = 0
names = ["Frame", "Draw the\nchain", "Close the\nfive gaps",
         "Cost and\ndefend"]
for (m, _, _), nm in zip(clock.MARKS, names):
    ax.add_patch(Rectangle((start, 1.9), m - start, 0.9, lw=0.75,
                           facecolor=fl.FILL["org"], edgecolor=fl.C["org"]))
    ax.text((start + m) / 2, 2.35, nm, ha="center", va="center",
            fontsize=9, color=fl.INK)
    ax.text(m, 3.05, f"{m}", ha="center", va="center", fontsize=9,
            fontweight="bold", color=fl.INK)
    start = m
ax.add_patch(Rectangle((0, 0.5), 3, 0.9, lw=0.75, facecolor="white",
                       edgecolor=fl.C["ops"]))
ax.add_patch(Rectangle((3, 0.5), 28, 0.9, lw=1.5, hatch=fl.HATCH[1],
                       facecolor=fl.FILL["fail"], edgecolor=fl.C["fail"]))
ax.text(17, 0.95, "The model", ha="center", va="center", fontsize=9,
        fontweight="bold", color=fl.LABEL["fail"],
        bbox=dict(facecolor="white", edgecolor="none", pad=1))
ax.add_patch(Rectangle((31, 0.5), 14, 0.9, lw=0.75, facecolor="white",
                       edgecolor=fl.C["ops"]))
ax.text(38, 0.95, "Chain at 31", ha="center", va="center", fontsize=9,
        color=fl.INK)
ax.text(0, 0.1, "The answer that began with the model", fontsize=9,
        color=fl.INK)
fl.save(fig)
