"""Figure 39.4  Canaries by task type.

Reading order: one bar per task type, highest daily volume at the top;
each bar splits 1,000 simulated canaries of a bundle that fails 3.7%
of runs against 0.7% into where it was stopped (5%, 25%, or 50%
exposure) and missed. Each segment has its own hatch. Low-volume task
types miss more at the same schedule. From release.canary.power
(Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from release import canary as C  # noqa: E402

types = list(C.VOLUME)
segs = ((0.05, "Stopped at 5%", "verified", fl.HATCH[0]),
        (0.25, "At 25%", "evidence", fl.HATCH[1]),
        (0.5, "At 50%", "ops", fl.HATCH[2]),
        ("missed", "Missed", "fail", fl.HATCH[3]))
fig, ax = fl.figure(4.0, 3.2)
for i, t in enumerate(types):
    res = C.power(0.037, 0.007, task_type=t)
    y = len(types) - 1 - i
    left = 0
    for k, lab, tok, h in segs:
        v = res.get(k, 0) / 10
        ax.barh(y, v, left=left, height=0.6, color=fl.FILL[tok],
                edgecolor=fl.C[tok], lw=0.9, hatch=h,
                label=lab if i == 0 else None)
        if k == "missed":
            ax.text(101, y, f"{v:.0f}%", va="center", fontsize=9,
                    color=fl.INK)
        left += v
ax.set_yticks(range(len(types)))
ax.set_yticklabels([f"{t.capitalize()}\n{C.VOLUME[t]} a day"
                    for t in reversed(types)])
ax.set_xlim(0, 115)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("Share of 1,000 simulated canaries, percent")
ax.set_ylim(-0.5, len(types) + 0.9)
ax.legend(fontsize=9, frameon=False, ncol=2, loc="upper center",
          handlelength=1.2, columnspacing=0.8)
fl.save(fig)
