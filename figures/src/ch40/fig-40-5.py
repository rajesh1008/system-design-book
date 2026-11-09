"""Figure 40.5  Onboarding time per use case.

Reading order: two bars, calendar days from start to live. The desk
assistant, June 22 to July 23, 2026, was onboarded by meeting: 31 days
and 11 meetings. Loyalty, August 17 to 26, took the paved road: 9 days
and one review. Segments are the logged stages. From
agentplatform.onboarding (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from agentplatform import onboarding as ob  # noqa: E402

fig, ax = fl.figure(4.2, 3.2)
bars = ((1, "Desk, by meeting", ob.DESK, "ops"),
        (0, "Loyalty, paved road", ob.LOYALTY, "verified"))
for y, name, stages, tok in bars:
    left = 0
    for i, s in enumerate(stages):
        ax.barh(y, s.days, left=left, height=0.5, color=fl.FILL[tok],
                edgecolor=fl.C[tok], lw=0.9, hatch=fl.HATCH[i % 2])
        left += s.days
    k = ob.meetings(stages)
    tail = "1 review" if k == 1 else f"{k} meetings"
    ax.text(left + 0.6, y, f"{ob.total(stages)} days, {tail}",
            va="center", fontsize=9, color=fl.LABEL[tok])
ax.set_yticks([0, 1])
ax.set_yticklabels(["Loyalty, paved road", "Desk, by meeting"])
ax.set_xlim(0, 46)
ax.set_ylim(-0.6, 1.6)
ax.set_xlabel("Calendar days from start to live")
fl.save(fig)
