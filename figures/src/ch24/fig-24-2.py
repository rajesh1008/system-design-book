"""Figure 24.2  Drift in retrieval quality over weeks.

Reading order: one line per index policy, recall at ten on the weekly
fresh sample of 200 questions, April 20 to June 8, 2026; the golden
set's recall is the flat dashed line. From knowops.weekly, seed 2026 (Lakeshore figures
are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from knowops import weekly  # noqa: E402

runs = {p: weekly.run(p) for p in ("frozen", "nightly", "contract")}
x = list(range(len(weekly.WEEKS)))
fig, ax = fl.figure(4.5, 3.2)
g = runs["nightly"][0]["golden"]
ax.axhline(g, color=fl.C["knowledge"], linestyle="--", lw=1)
ax.text(3.5, 100.5, "golden set", fontsize=9.5, ha="center",
        color=fl.C["knowledge"])
style = {"frozen": ("fail", "index frozen May 4"),
         "nightly": ("ops", "nightly crawl"),
         "contract": ("verified", "15-min contract")}
for i, (p, rows) in enumerate(runs.items()):
    tok, lab = style[p]
    ys = [r["fresh"] for r in rows]
    ax.plot(x, ys, color=fl.C[tok], lw=fl.STROKE["emphasis"]
            if p == "nightly" else 1.2, marker=fl.MARKERS[i],
            label=lab)
ax.set_xticks(x)
ax.set_xticklabels([w.strftime("%b %-d") for w in weekly.WEEKS],
                   rotation=45, ha="right")
ax.set_xlabel("Week of, 2026")
ax.set_ylabel("Fresh-sample recall at ten (%)")
ax.set_ylim(84, 101.5)
ax.legend(loc="lower left", fontsize=9, frameon=False)
fl.save(fig)
