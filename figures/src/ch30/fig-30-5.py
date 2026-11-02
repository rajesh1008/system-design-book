"""Figure 30.5  Lock-in by plane.

Reading order: one pair of bars per plane; the items on Daniel
Price's exit list if Lakeshore adopted every service the runtime
sells, against the list under the decision. Illustrative counts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

planes = ("Action", "Control", "Knowledge", "Trail")
all_in = (3, 3, 2, 2)
decided = (2, 0, 0, 0)
fig, ax = fl.figure(4.5, 3.0)
ys = range(len(planes))
h = 0.36
ax.barh([y + h / 2 for y in ys], all_in, height=h, color=fl.C["org"],
        label="Every service")
ax.barh([y - h / 2 for y in ys], decided, height=h, color=fl.C["ops"],
        label="As decided")
for y, a, d in zip(ys, all_in, decided):
    ax.text(a + 0.06, y + h / 2, str(a), va="center", fontsize=9,
            color=fl.INK)
    ax.text(d + 0.06, y - h / 2, str(d), va="center", fontsize=9,
            color=fl.INK)
ax.set_yticks(list(ys))
ax.set_yticklabels(planes, fontsize=9)
ax.invert_yaxis()
ax.set_xlim(0, 4)
ax.set_xticks([0, 1, 2, 3, 4])
ax.set_xlabel("Items to rebuild at exit", fontsize=9)
ax.tick_params(labelsize=9)
ax.legend(fontsize=9, frameon=False, loc="lower right")
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fl.save(fig)
