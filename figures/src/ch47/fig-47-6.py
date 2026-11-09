"""Figure 47.5  The question bank by round and level.

Reading order: one bar per round tag, in loop order from the phone
screen at the top to the hiring manager at the bottom; each bar is
split by tier, mid to principal, left to right, with the total at
the end. The take-home bar is the thin one. From bank.appendix over
the committed index, bank/data/bank-index.tsv (702 questions).
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from bank.manuscript import SNAPSHOT, load_snapshot  # noqa: E402
from bank.taxonomy import ROUNDS, TIER_LEVEL  # noqa: E402

SHORT = {"phone-screen": "Phone screen", "system-design": "Design",
         "distributed-systems": "Distributed",
         "agent-runtime": "Harness", "control-plane-security": "Control",
         "evaluation-operations": "Eval and ops",
         "take-home": "Take-home", "bar-raiser": "Bar-raiser",
         "hiring-manager": "Hiring manager"}
rows = load_snapshot(SNAPSHOT)
count = Counter((r["loop_round"], r["level"]) for r in rows)
tags = list(ROUNDS)
tiers = list(TIER_LEVEL)
fig, ax = fl.figure(4.4, 3.6)
for i, tag in enumerate(tags):
    y = len(tags) - 1 - i
    left = 0
    for j, tier in enumerate(tiers):
        n = count[(tag, tier)]
        ax.barh(y, n, left=left, height=0.62, color=fl.FILL["org"],
                edgecolor=fl.C["org"], lw=0.8, hatch=fl.HATCH[j])
        left += n
    ax.text(left + 2, y, str(left), va="center", fontsize=9,
            color=fl.INK)
ax.set_yticks(range(len(tags)))
ax.set_yticklabels([SHORT[t] for t in reversed(tags)])
ax.set_xlim(0, 180)
ax.set_xlabel("Questions in the bank")
ax.tick_params(labelsize=9)
ax.legend(handles=[Patch(facecolor=fl.FILL["org"], edgecolor=fl.C["org"],
                         hatch=fl.HATCH[j], label=t)
                   for j, t in enumerate(tiers)],
          loc="center right", fontsize=9, frameon=False)
fl.save(fig)
