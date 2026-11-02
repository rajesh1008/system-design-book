"""Figure 14.7  Acceptance rate against speed-up, by batch size.

Reading order: left to right. Each line is one batch size; above the
dashed line speculative decoding pays, below it the extra verify work
costs more than it saves. k = 4, draft cost 0.05 of a target step. From
serving.speculative.speedup (lab model, engine A step profile).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from serving import speculative as sp  # noqa: E402

xs = [a / 100 for a in range(20, 91, 5)]
fig, ax = fl.figure(4.5, 3.4)
for i, (b, col) in enumerate(((1, "model"), (8, "ops"), (64, "evidence"),
                              (128, "policy"))):
    ys = [sp.speedup(a, 4, 0.05, b) for a in xs]
    ax.plot(xs, ys, color=fl.C[col], lw=1.5, ls=fl.LINESTYLES[i], marker="")
    fl.label_line(ax, 0.905, ys[-1], f"batch {b}", color=fl.LABEL[col])
ax.axhline(1.0, color=fl.INK, lw=0.75, ls="--")
ax.axvline(0.4, color=fl.INK, lw=0.75, ls=":")
ax.text(0.41, 2.9, "40% acceptance", fontsize=9.5, color=fl.INK)
ax.set_xlim(0.2, 1.08)
ax.set_xticks([0.2, 0.4, 0.6, 0.8])
ax.set_xticklabels(["20%", "40%", "60%", "80%"])
ax.set_xlabel("Draft tokens accepted")
ax.set_ylabel("Speed-up over plain decoding")
fl.save(fig)
