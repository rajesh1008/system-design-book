"""Figure 18.9  Cost per verified outcome against baseline.

Reading order: left to right by month. Bars are the agent's cost per
verified outcome from the scoreboard; the lines are the paths it
replaces or sits beside. Values from the scoreboard and Chapter 4.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

months = ("Dec 2025", "Mar 2026", "Apr 2026", "May 2026")
vals = (4.10, 2.60, 2.95, 1.84)
fig, ax = fl.figure(4.5, 3.2)
ax.bar(range(4), vals, width=0.55, color=fl.FILL["verified"],
       edgecolor=fl.C["verified"], lw=0.75)
for x, v in enumerate(vals):
    ax.text(x, v + 0.6, f"${v:.2f}", ha="center", fontsize=9.5,
            color=fl.INK)
for y, label, ls in ((37.94, "Baseline blend $37.94", "-"),
                     (11.40, "Self-service $11.40", "--"),
                     (6.20, "Assisted $6.20", ":")):
    ax.axhline(y, color=fl.C["org"], lw=1.0, ls=ls)
    ax.text(3.35, y + 0.7, label, fontsize=9.5, color=fl.INK, ha="right")
ax.set_xticks(range(4))
ax.set_xticklabels(months, fontsize=9.5)
ax.set_ylim(0, 42)
ax.set_ylabel("Dollars per verified outcome")
fl.save(fig)
