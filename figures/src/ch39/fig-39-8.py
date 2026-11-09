"""Figure 39.8  The change scorecard, August 31, 2026.

Reading order: one row per line of the card, top to bottom: releases,
the June count, exposure paths, rollbacks, regressions in production,
and unbundled changes found by the trail check; the value and what it
is for. Rows that close the chapter's question are highlighted, and
say so in words. From release.log.card (Lakeshore figures are
illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from release import log as L  # noqa: E402

c = L.counts()
rows = [("Releases", f"{c['releases']} of {c['kinds']} kinds",
         "All", "ops"),
        ("June's rule", str(c["june_rule"]), "Deploys seen", "ops"),
        ("Shadow", str(c["shadowed"]), "No effects", "ops"),
        ("Canary", str(c["canaried"]), "Per task type", "ops"),
        ("Fixed horizon", str(c["ab"]), "Notices", "ops"),
        ("Rolled back", str(len(c["rolled_back"])), "At canary",
         "verified"),
        ("Prod. regressions", str(c["production_regressions"]),
         "Goal", "verified"),
        ("Unbundled", "0", "Daily check", "verified")]
heads = ("Line", "Value", "Reading")
cols = (0.0, 1.95, 3.15)
fig, ax = fl.figure(4.5, 3.3)
n = len(rows)
ax.set_xlim(0, 5.1)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 5.1, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=1.5 if tok == "verified" else 0.75))
    for x, s in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, s, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x == cols[0] else None)
fl.save(fig)
