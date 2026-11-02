"""Figure 38.8  The storm with and without the cap.

Reading order: left to right across the weekend of July 25 and 26,
CDT; the waiver watch's billed dollars so far on a log scale, as run
and replayed under DR-38.1. The replay pages at half and stops at the
limit each day; the as-run line never meets a stop. From
economics.replay (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from economics import replay  # noqa: E402
from economics.policy import DR38, JULY  # noqa: E402

t0 = replay.run(JULY).path[0][0]
fig, ax = fl.figure(4.5, 3.0)
for pol, tok, ls, lab in ((JULY, "fail", "-", "As run"),
                          (DR38, "verified", "--", "DR-38.1")):
    p = replay.run(pol).path
    xs = [(t - t0).total_seconds() / 3600 + 2 + 14 / 60 for t, _ in p]
    ys = [max(v, 0.01) for _t, v in p]
    ax.plot(xs, ys, color=fl.C[tok], ls=ls, lw=1.6, marker="",
            label=lab)
    ax.text(xs[-1] - 0.5, ys[-1] * 1.35, f"${ys[-1]:,.0f}", ha="right",
            fontsize=9, color=fl.INK)
ax.set_yscale("log")
ax.set_ylim(0.01, 40000)
ax.axvline(24, color=fl.INK, lw=0.5, ls=":")
ax.text(24.3, 0.02, "Sunday", fontsize=9, color=fl.INK)
ax.set_xlabel("Hours from Saturday midnight, CDT")
ax.set_ylabel("Billed so far, dollars")
ax.legend(fontsize=9, frameon=False, loc="upper left")
fl.save(fig)
