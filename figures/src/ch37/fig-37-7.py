"""Figure 37.6  Time to stop by incident.

Reading order: left to right, one row of stop facts per incident: from
the decision to the far end's count staying flat. The July 26 stop is
shown as run (tier two, then tier three) and with tier three first.
The 90 s target is dashed. From reliability.stop (Lakeshore figures
are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from reliability import stop  # noqa: E402

rows = (("July 8, tier one", stop.july8(), "ops"),
        ("July 26, as run", stop.storm(), "ops"),
        ("July 26, tier three first", stop.storm([(9, 3, "x", "")]), "verified"))
fig, ax = fl.figure(4.5, 3.0)
for i, (lab, s, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    secs = s.seconds
    ax.barh(y, secs, height=0.5, color=fl.FILL[tok], edgecolor=fl.C[tok],
            lw=1.5 if tok == "verified" else 0.75,
            hatch="///" if tok == "verified" else "")
    ax.text(secs + 2, y, f"{secs:.0f} s", va="center", fontsize=9,
            color=fl.INK)
    ax.text(1, y + 0.4, lab, fontsize=9, color=fl.INK)
ax.axvline(90, color=fl.INK, lw=0.75, ls="--")
ax.text(91, 2.55, "Target 90 s", fontsize=9, color=fl.INK)
ax.set_yticks([])
ax.set_ylim(-0.5, 2.95)
ax.set_xlim(0, 135)
ax.set_xlabel("Seconds from decision to safe state")
fl.save(fig)
