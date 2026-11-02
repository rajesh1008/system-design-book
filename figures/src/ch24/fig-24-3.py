"""Figure 24.3  Golden set against fresh sample.

Reading order: two groups of bars, fare-rule questions and waiver
questions, recall at ten for the golden set and for the fresh sample
of the week of May 4, 2026, under the nightly crawl. The golden set's
waiver questions are all about notices it already held; the fresh
sample's include notices posted on Saturday, May 9. From
knowops.weekly and knowops.drift, seed 2026 (Lakeshore figures are
illustrative).
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from knowops import weekly  # noqa: E402
from knowops.drift import recall  # noqa: E402

w = date(2026, 5, 4)
sets = {"Golden set": weekly.golden(), "Fresh sample": weekly.fresh_sample(w)}
slices = (("rule", "Fare-rule questions"), ("notice", "Waiver questions"))
fig, ax = fl.figure(4.5, 3.3)
width = 0.36
for k, (name, qs) in enumerate(sets.items()):
    tok = "knowledge" if k == 0 else "ops"
    for i, (sl, _) in enumerate(slices):
        sub = [q for q in qs if weekly.slice_of(q) == sl]
        r, _m = recall(sub, "nightly")
        fail = (k == 1 and sl == "notice")
        t = "fail" if fail else tok
        xpos = i + (k - 0.5) * width
        ax.bar(xpos, r, width=width * 0.92, color=fl.FILL[t],
               edgecolor=fl.C[t], lw=0.75,
               label=name if i == 0 else None)
        ax.text(xpos, r + 2, f"{r:.0f}%\n({len(sub)})", ha="center", va="bottom",
                fontsize=9, color=fl.LABEL["fail"] if fail else fl.INK)
ax.set_xticks([0, 1])
ax.set_xticklabels([s[1] for s in slices])
ax.set_ylim(0, 125)
ax.set_ylabel("Recall at ten (%)")
ax.legend(loc="lower right", fontsize=9, frameon=False)
fl.save(fig)
