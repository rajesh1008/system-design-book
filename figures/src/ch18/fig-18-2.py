"""Figure 18.2  Where the money goes in one task.

Reading order: top to bottom, largest line first. May 2026, dollars
per verified outcome; people's minutes are review, rework, and repeat
contacts. From cost.demo --part unit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from cost.unit import MAY, month_cost  # noqa: E402

c = month_cost(MAY)
ln, n = c["lines"], c["verified"]
rows = [("People's minutes", (ln["review labor"] + ln["rework"]
                              + ln["repeat contacts"]) / n, "ops"),
        ("Platform", ln["platform"] / n, "ops"),
        ("Tools and fees", ln["tools and fees"] / n, "ops"),
        ("Verification", ln["verification"] / n, "ops"),
        ("Model tokens", ln["model tokens"] / n, "model")]
fig, ax = fl.figure(4.5, 3.4)
for i, (label, v, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.barh(y, v, color=fl.FILL[tok], edgecolor=fl.C[tok], lw=0.75,
            height=0.6)
    ax.text(v + 0.02, y, f"${v:.3f}", va="center", fontsize=9.5,
            color=fl.INK)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in reversed(rows)], fontsize=9.5)
ax.set_xlim(0, 1.2)
ax.set_xlabel(f"Dollars per verified outcome, total ${c['per_outcome']:.2f}")
ax.text(0.30, 0.0, f"{ln['model tokens'] / c['total']:.1%} of the total",
        va="center", fontsize=9.5, color=fl.INK, style="italic")
fl.save(fig)
