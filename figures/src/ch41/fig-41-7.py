"""Figure 41.7  The team over the year.

Reading order: months of 2026 left to right; the solid line is people
seated on Daniel Price's platform team at the end of each month, and
the dashed line from August adds the two signed hires on their start
dates. Labels mark when each role arrived. Year end: eleven. From the
team card (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
          "Sep", "Oct", "Nov", "Dec"]
seated = [5, 5, 6, 6, 7, 8, 9, 9]
planned = [9, 11, 11, 11, 11]
fig, ax = fl.figure(4.5, 3.2)
ax.plot(range(8), seated, color=fl.C["org"], lw=1.8, marker="o",
        ms=4)
ax.plot(range(7, 12), planned, color=fl.C["org"], lw=1.5, ls="--",
        marker="s", ms=4)
for x, y, t in ((1.0, 7.4, "evaluation\nengineer"),
                (3.7, 4.6, "agent\nengineer"),
                (3.9, 9.7, "platform\nengineer"),
                (6.2, 7.3, "second\nSRE"),
                (5.6, 12.4, "architect, eval. engineer")):
    ax.text(x, y, t, fontsize=9, color=fl.INK, va="center")
ax.set_xticks(range(12))
ax.set_xticklabels(months)
ax.set_ylim(0, 13.2)
ax.set_ylabel("People on the team")
fl.save(fig)
