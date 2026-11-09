"""Figure 32.7  Exposure against credential lifetime.

Reading order: left to right, token lifetime on a log scale from one
minute to about a week. Each line is the share of 2,000 simulated leaked tokens
still alive when someone tried them, for a finder who takes a median
45 minutes and one who takes 10. The marks are 15 minutes and one
hour. From identity.exposure.curve; the delays are assumptions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from identity import exposure  # noqa: E402

fig, ax = fl.figure(4.5, 3.2)
for i, (med, tok, lw) in enumerate(((45, "policy", 2.0),
                                    (10, "fail", 1.25))):
    pts = exposure.curve(points=40, median_min=med)
    ax.plot([p[0] for p in pts], [100 * p[1] for p in pts],
            color=fl.C[tok], ls=fl.LINESTYLES[i], lw=lw,
            label=f"Found after a median {med} min")
ax.set_xscale("log")
for m, txt in ((15, "15 min"), (60, "1 hour")):
    ax.axvline(m, color=fl.GREY_LIGHT, lw=0.75)
    fl.label_line(ax, m, 92, txt, dx=3)
ax.set_xlim(1, 10000)
ax.set_ylim(0, 100)
ax.set_xticks([1, 10, 100, 1000, 10000])
ax.set_xticklabels(["1 min", "10", "100", "1,000", "10,000"])
ax.set_ylabel("Leaked tokens that worked (%)")
ax.legend(loc="lower right", frameon=False, fontsize=9)
fl.save(fig)
