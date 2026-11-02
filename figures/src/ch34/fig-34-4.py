"""Figure 34.4  Judge agreement with people.

Reading order: left panel, the 300 held-out messages, the judge's
verdict against the desk's label; right panel, kappa for each
calibration against the bar of 0.75. Values from evals.demo
--part judge and evals.live --replay. Lakeshore figures are
illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

fig, (a, b) = fl.figure(4.5, 3.1, ncols=2,
                        gridspec_kw={"width_ratios": [1.0, 1.15]})
cells = ((266, "verified", "Both pass"), (10, "fail", "Judge pass,\npeople fail"),
         (0, "fail", "Judge fail,\npeople pass"), (24, "verified", "Both fail"))
for i, (n, tok, lab) in enumerate(cells):
    y = 3 - i
    a.barh(y, n, color=fl.FILL[tok], edgecolor=fl.C[tok], lw=0.75,
           hatch=fl.HATCH[0 if tok == "verified" else 1])
    a.text(n + 6, y, str(n), va="center", fontsize=9, color=fl.INK)
a.set_yticks([3, 2, 1, 0])
a.set_yticklabels([c[2] for c in cells], fontsize=9)
a.set_xlim(0, 330)
a.set_xticks([0, 100, 200])
a.set_title("Held-out messages, 300", fontsize=9.5, color=fl.INK)
runs = (("Pin 05-12", 0.81, "verified"), ("Pin 06-30", 0.79, "verified"),
        ("Live, 30", 0.86, "verified"))
for i, (lab, k, tok) in enumerate(runs):
    b.bar(i, k, color=fl.FILL[tok], edgecolor=fl.C[tok], lw=0.75, width=0.6)
    b.text(i, k + 0.015, f"{k:.2f}", ha="center", fontsize=9, color=fl.INK)
b.axhline(0.75, color=fl.C["fail"], lw=1.5, ls="--")
b.text(2.45, 0.725, "Bar 0.75", ha="right", va="top", fontsize=9,
       color=fl.LABEL["fail"])
b.set_xticks(range(3))
b.set_xticklabels([r[0] for r in runs], fontsize=9)
b.set_ylim(0.5, 0.95)
b.set_title("Kappa with people", fontsize=9.5, color=fl.INK)
fl.save(fig)
