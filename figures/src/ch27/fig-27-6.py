"""Figure 27.6  Debate, voting, and one agent with a verifier.

Reading order: left to right, tokens as a multiple of one agent;
bottom to top, correct answers on the 24 eligibility tasks, 25 runs a
task. Filled markers: the lab's correlated agents (correlation 0.65);
hollow markers: the same designs with independent agents, the case
the research assumes. From topology.vote. Lakeshore figures are
illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import figlib as fl  # noqa: E402

pts = (("One agent", 1.00, 89.5, "model", "o"),
       ("Agent and verifier", 1.11, 95.7, "verified", "s"),
       ("Vote of three", 3.00, 91.2, "ops", "^"),
       ("Debate", 7.48, 90.8, "fail", "D"))
ind = (("Vote, independent", 3.00, 96.2, "ops", "^"),
       ("Debate, independent", 7.48, 94.7, "fail", "D"))
fig, ax = fl.figure(4.5, 3.2)
for name, x, yv, tok, m in pts:
    ax.scatter(x, yv, s=46, color=fl.C[tok], marker=m, zorder=3)
    fl.label_line(ax, x, yv, name, dx=6, dy=-2)
for name, x, yv, tok, m in ind:
    ax.scatter(x, yv, s=46, facecolor="white", edgecolor=fl.C[tok],
               lw=1.5, marker=m, zorder=3)
    fl.label_line(ax, x, yv, name, dx=6, dy=2)
ax.set_xlim(0.5, 10.8)
ax.set_ylim(87, 98)
ax.set_xlabel("Tokens, multiple of one agent")
ax.set_ylabel("Correct, %")
ax.grid(True)
fl.save(fig)
