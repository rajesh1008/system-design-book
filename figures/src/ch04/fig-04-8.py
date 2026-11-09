"""Figure 4.1  The scoreboard at baseline.

Reading order: one row per scoreboard column, top to bottom, for the
12 months to September 30, 2025. Measured values are solid; columns with
nothing to measure yet are dashed and read n/a. Values from
python3 -m baseline.demo (corpus ops-v1, seed 2026).
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Agent", "0%"), ("Assisted", "0%"), ("Self-service", "39%"),
        ("Person", "61%"), ("Cost per verified outcome", "n/a"),
        ("Blended cost per change", "$37.94"),
        ("Verified-outcome rate", "n/a"), ("Duplicates", "n/a"),
        ("Unauthorized", "0"), ("Incidents", "0"), ("p95 latency", "n/a"),
        ("Use cases", "1")]
fig, ax = fl.figure(4.5, 4.6)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(0, n + 1.0)
ax.axis("off")
ax.text(0.1, n + 0.5, "Baseline, 12 months to Sep. 30, 2025",
        va="center", fontweight="bold", color=fl.LABEL["org"])
for i, (name, val) in enumerate(rows):
    y = n - i - 0.5
    na = val == "n/a"
    ax.text(0.1, y, name, va="center")
    tok = "org" if na else ("evidence" if name.startswith("Blended") else "ops")
    ax.add_patch(Rectangle((6.6, y - 0.36), 3.3, 0.72,
                           facecolor="white" if na else fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"],
                           linestyle="--" if na else "-"))
    ax.text(8.25, y, val, va="center", ha="center",
            color=fl.LABEL[tok] if na else fl.TEXT_ON[tok],
            fontweight="normal" if na else "bold")
fl.save(fig)
