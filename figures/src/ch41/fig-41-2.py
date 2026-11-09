"""Figure 41.2  What the postings ask for.

Reading order: one bar per skill, top to bottom, in the order Chapter
41 uses; the bar is the number of the 47 postings (29 employers, as of
November 2, 2026) whose paraphrased skills name it, with the count and
share at the bar's end. Control is the shortest of the six. From
bank.market (keyword tagging, a reading aid).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from bank import market  # noqa: E402

ps = market.load()
c = market.counts(ps)
names = {"distributed": "Distributed systems", "models": "Models",
         "retrieval": "Retrieval", "control": "Control",
         "evaluation": "Evaluation", "operations": "Operations",
         "field": "Customer-facing"}
tags = list(market.TAGS)
fig, ax = fl.figure(4.0, 3.4)
for i, t in enumerate(tags):
    y = len(tags) - 1 - i
    ax.barh(y, c[t], height=0.6, color=fl.FILL["org"],
            edgecolor=fl.C["org"], lw=0.9,
            hatch="///" if t == "field" else "")
    ax.text(c[t] + 0.4, y, f"{c[t]}  ({c[t] / len(ps):.0%})",
            va="center", fontsize=9.5, color=fl.INK)
ax.set_yticks(range(len(tags)))
ax.set_yticklabels([names[t] for t in reversed(tags)], fontsize=9.5)
ax.tick_params(axis="x", labelsize=9.5)
ax.set_xlim(0, 25)
ax.set_xlabel(f"Postings naming the skill, of {len(ps)}", fontsize=9.5)
fl.save(fig)
