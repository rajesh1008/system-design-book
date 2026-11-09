"""Figure 23.4  Confidence thresholds and routing.

Reading order: left to right along the threshold. Bars are the share
of 2,000 seeded reads sent to review; the two lines are the error
rate among accepted values, with and without the record check. From
inputs.route.sweep (the lab's thresholds part).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from inputs.route import population, sweep  # noqa: E402

rows = sweep(population())
t = [r["t"] for r in rows]
fig, ax = fl.figure(4.5, 3.4)
ax2 = ax.twinx()
ax2.bar(range(len(t)), [r["review"] / 2000 * 100 for r in rows], width=0.6,
        color=fl.FILL["knowledge"], edgecolor=fl.C["knowledge"], lw=0.75,
        hatch=fl.HATCH[1], zorder=0)
ax2.set_ylabel("Sent to review, % of reads", fontsize=9.5)
ax2.set_ylim(0, 100)
ax.set_zorder(ax2.get_zorder() + 1)
ax.patch.set_visible(False)
ax.plot(range(len(t)), [r["err"] * 100 for r in rows], color=fl.C["fail"],
        marker=fl.MARKERS[0], ls=fl.LINESTYLES[0])
ax.plot(range(len(t)), [r["err_chk"] * 100 for r in rows],
        color=fl.C["verified"], marker=fl.MARKERS[1], ls=fl.LINESTYLES[1])
ax.set_xticks(range(len(t)))
ax.set_xticklabels([f"{x:.2f}" for x in t], fontsize=9, rotation=45)
ax.set_xlabel("Accept threshold on extractor confidence")
ax.set_ylabel("Error among accepted, %")
ax.set_ylim(0, 14)
fl.label_line(ax, 0.2, rows[0]["err"] * 100 + 0.6, "threshold only",
              color=fl.LABEL["fail"])
ax.annotate("with record check", xy=(1, 0.06), xytext=(1.6, 2.9),
            fontsize=9.5, color=fl.LABEL["verified"],
            bbox=dict(boxstyle="square,pad=0.2", fc="white", ec="none"),
            arrowprops=dict(arrowstyle="-", color=fl.C["verified"], lw=0.75))
fl.save(fig)
