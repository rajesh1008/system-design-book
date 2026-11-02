"""Figure 27.7  Coordination tokens by topology.

Reading order: three pairs of bars, one agent above orchestrator-worker
in each: all cases, cases of one or two legs, cases of three or more
legs. Orchestrator bars split into coordination (briefs, worker
prompts, summaries read back) and work. Tokens a task, from
topology.compare on the 1,200-case golden set, three runs a case.
Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import figlib as fl  # noqa: E402

groups = ("All cases", "1 or 2 legs", "3 or more legs")
single = (59705, 46826, 173497)
ow_total = (96618, 91593, 141020)
ow_coord = (59807, 55275, 99856)
fig, ax = fl.figure(4.5, 3.2)
y = [7, 6, 4, 3, 1, 0]
for i, g in enumerate(groups):
    ys, yo = y[2 * i], y[2 * i + 1]
    ax.barh(ys, single[i], color=fl.FILL["model"], edgecolor=fl.C["model"],
            height=0.7, hatch="///")
    ax.barh(yo, ow_coord[i], color=fl.C["ops"], edgecolor=fl.C["ops"],
            height=0.7)
    ax.barh(yo, ow_total[i] - ow_coord[i], left=ow_coord[i],
            color=fl.FILL["ops"], edgecolor=fl.C["ops"], height=0.7)
    fl.label_line(ax, single[i], ys, f"{single[i]:,}")
    fl.label_line(ax, ow_total[i], yo, f"{ow_total[i]:,}")
ax.set_yticks(y)
ax.set_yticklabels(["One agent", "Orchestrator"] * 3)
for yy, g in zip((7.75, 4.75, 1.75), groups):
    ax.text(0, yy, g, fontsize=9, fontweight="bold", color=fl.INK,
            va="center")
ax.set_ylim(-0.6, 8.2)
ax.set_xlim(0, 215000)
ax.set_xticks([0, 50000, 100000, 150000, 200000])
ax.set_xticklabels(["0", "50,000", "100,000", "150,000", "200,000"])
ax.set_xlabel("Tokens a task (dark: coordination)")
ax.grid(axis="x")
fl.save(fig)
