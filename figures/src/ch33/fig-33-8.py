"""Figure 33.8  Battery results: how far each attack traveled.

Reading order: one stacked bar per attack class, top to bottom; each
segment is the furthest stage the attack reached. Values from
threats.demo --part battery (61 attacks, 0 effects).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

classes = ("Direct", "Indirect", "Poisoning", "Memory", "Exfiltration",
           "Deputy")
data = {"Entry": (0, 12, 7, 6, 0, 0),
        "Context": (2, 0, 0, 0, 0, 0),
        "Refused": (5, 2, 3, 1, 10, 9),
        "Proposal": (1, 2, 0, 1, 0, 0),
        "Effect": (0, 0, 0, 0, 0, 0)}
face = {"Entry": fl.C["verified"], "Context": fl.FILL["verified"],
        "Refused": fl.FILL["policy"], "Proposal": fl.FILL["fail"],
        "Effect": fl.C["fail"]}
edge = {"Entry": fl.C["verified"], "Context": fl.C["verified"],
        "Refused": fl.C["policy"], "Proposal": fl.C["fail"],
        "Effect": fl.C["fail"]}
fig, ax = fl.figure(4.5, 3.0)
ys = [len(classes) - 1 - i for i in range(len(classes))]
left = [0] * len(classes)
for stage, vals in data.items():
    ax.barh(ys, vals, left=left, color=face[stage], edgecolor=edge[stage],
            height=0.6)
    left = [a + b for a, b in zip(left, vals)]
for y, total in zip(ys, left):
    fl.label_line(ax, total, y, str(total))
ax.set_yticks(ys)
ax.set_yticklabels(classes)
ax.set_xlim(0, 19)
ax.legend(handles=[Patch(facecolor=face[s], edgecolor=edge[s], label=s)
                   for s in data],
          loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
          fontsize=9, frameon=False)
ax.set_xlabel("Attacks (61; 0 reach an effect)")
ax.grid(axis="x")
fl.save(fig)
