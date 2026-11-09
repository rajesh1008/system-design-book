"""Figure 31.10  Time to stop by tier.

Reading order: one group per tier, left to right; nine Thursday drills
from April 30 to June 25, 2026, the median marked, and the 90 s target.
From policy.drill (lab replay; Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from policy import drill as D  # noqa: E402

fig, ax = fl.figure(4.5, 3.0)
names = {1: "Tier one", 2: "Tier two", 3: "Tier three"}
for tier in (1, 2, 3):
    xs = [r.time_to_stop for r in D.weekly(tier)]
    jitter = [tier + (i - 4) * 0.035 for i in range(len(xs))]
    ax.scatter(jitter, xs, s=14, color=fl.C["ops"], zorder=3)
    med = D.medians()[tier]
    ax.plot([tier - 0.25, tier + 0.25], [med, med], color=fl.C["verified"],
            lw=2)
    ax.text(tier + 0.34, med, f"{med:.0f} s", va="center", fontsize=9,
            color=fl.INK)
ax.axhline(90, color=fl.C["fail"], lw=1, ls="--")
ax.text(0.6, 92, "Target 90 s", fontsize=9, color=fl.INK)
ax.set_xticks([1, 2, 3], [names[t] for t in (1, 2, 3)])
ax.set_xlim(0.5, 3.7)
ax.set_ylim(0, 100)
ax.set_ylabel("Seconds to safe state")
fl.save(fig)
