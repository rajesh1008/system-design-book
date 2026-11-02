"""Figure 10.4  The p95 that lied: per call and per task.

Reading order: left to right on a log time axis. The left curve is
every accepted model call; the right curve is every task, as run. The
dotted markers are each curve's p95. From 04-code/designlab, seed 10.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from corpus.traces import generate_traces  # noqa: E402
from capacity import budget as B  # noqa: E402
from capacity.stats import pct  # noqa: E402

S = generate_traces(10)
calls = sorted(c for s in S for x in s.steps for c in x.model_s)
tasks = sorted(B.replay(S, B.AS_RUN).latencies)
fig, ax = fl.figure(4.5, 3.4)
for xs, col, ls, name, lx in ((calls, "model", "-", "per call", 0.25),
                              (tasks, "fail", "--", "per task", 4.3)):
    ys = [100 * (i + 1) / len(xs) for i in range(len(xs))]
    ax.plot(xs, ys, color=fl.C[col], lw=1.5, ls=ls, marker="")
    p = pct(xs, 0.95)
    ax.axvline(p, color=fl.INK, lw=0.75, ls=":")
    ax.text(p * 1.08, 40, f"p95 {p:.1f} s", fontsize=9.5, color=fl.INK,
            rotation=90, va="center")
    fl.label_line(ax, lx, 70 if lx < 1 else 50, name, color=fl.LABEL[col], dx=0)
ax.annotate("", xy=(52.2, 95), xytext=(1.9, 95),
            arrowprops=dict(arrowstyle="-|>", lw=2.5 * 0.6, color=fl.INK))
ax.set_xscale("log")
ax.set_xlim(0.15, 200)
ax.set_xticks([0.2, 1, 5, 20, 100])
ax.set_xticklabels(["0.2", "1", "5", "20", "100"])
ax.set_xlabel("Seconds (log scale)")
ax.set_ylabel("Share at or below (%)")
fl.save(fig)
