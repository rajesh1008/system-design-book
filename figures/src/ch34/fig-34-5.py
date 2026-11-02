"""Figure 34.5  pass at k against pass^k.

Reading order: left to right, k from 1 to 8 trials per task on
R-0617, 640 tasks. pass@k rises toward 1; pass^k falls. Values from
evals.demo --part passk. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

ks = [1, 2, 3, 5, 8]
at = [0.9936, 0.9999, 1.0, 1.0, 1.0]
hat = [0.9936, 0.9872, 0.9810, 0.9689, 0.9516]
fig, ax = fl.figure(4.5, 3.0)
ax.plot(ks, at, color=fl.C["verified"], ls=fl.LINESTYLES[0], lw=1.5,
        marker=fl.MARKERS[0])
ax.plot(ks, hat, color=fl.C["fail"], ls=fl.LINESTYLES[1], lw=2.5,
        marker=fl.MARKERS[1])
fl.label_line(ax, 8, 1.0, "pass@k", dy=-6)
fl.label_line(ax, 8, 0.9516, "pass^k")
ax.axhline(1.0, color=fl.GREY_LIGHT, lw=0.75)
ax.annotate("Gate reads k = 3: 0.981", xy=(3, 0.981), xytext=(1.0, 0.955),
            fontsize=9, color=fl.INK,
            arrowprops={"arrowstyle": "-", "color": fl.GREY_DARK, "lw": 0.75})
ax.set_xlim(0.6, 9.6)
ax.set_ylim(0.94, 1.006)
ax.set_xticks(ks)
ax.set_xlabel("Trials per task, k")
ax.set_ylabel("Share of 640 tasks")
fl.save(fig)
