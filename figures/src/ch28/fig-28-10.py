"""Figure 28.10  Loop runs against budget, June 12 to 28, 2026.

Reading order: left to right, one bar per day: the fare watch's
settled model spend. The solid line is its loop-day budget of $20,
the dashed line the 80% alert; the dotted line is the $5 loop day of
the Try It Yourself box. June 16 is the fare sale. Values from
loops.demo --part budget. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

spend = (2.03, 1.78, 1.87, 1.76, 7.28, 1.44, 1.21, 1.70, 1.46, 1.27,
         1.37, 1.17, 1.21, 1.39, 1.39, 1.48, 1.23)
days = list(range(12, 12 + len(spend)))
fig, ax = fl.figure(4.5, 3.0)
cols = [fl.C["model"] if d != 16 else fl.C["ops"] for d in days]
ax.bar(days, spend, color=cols, width=0.7)
ax.axhline(20, color=fl.C["policy"], lw=1.5, ls=fl.LINESTYLES[0])
ax.axhline(16, color=fl.C["policy"], lw=1.0, ls=fl.LINESTYLES[1])
ax.axhline(5, color=fl.C["fail"], lw=1.0, ls=fl.LINESTYLES[3])
ax.text(28.6, 20.5, "Loop day $20", ha="right", fontsize=9,
        color=fl.INK)
ax.text(28.6, 16.5, "Alert 80%", ha="right", fontsize=9, color=fl.INK)
ax.text(28.6, 5.5, "Try it: $5", ha="right", fontsize=9, color=fl.INK)
fl.label_line(ax, 16.4, 7.28, "Fare sale", dx=0)
ax.set_xlim(11.3, 28.7)
ax.set_ylim(0, 22)
ax.set_xticks([12, 16, 20, 24, 28])
ax.set_xticklabels(["Jun 12", "16", "20", "24", "28"])
ax.set_ylabel("Model spend per day ($)")
ax.grid(axis="y")
fl.save(fig)
