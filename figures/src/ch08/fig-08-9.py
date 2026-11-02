"""Figure 8.9  Absorb rates by consumer.

Reading order: top to bottom, fastest producer first. Items a minute
each stage can absorb, on a log scale. The people are three orders of
magnitude slower than the rule that feeds them. Lab values from
python3 -m spine.demo (seed 8).
"""
import figlib as fl

rows = [("Seat search", 1200, "ops"),
        ("Refund proposals", 400, "ops"),
        ("Desk, 10 reviewers", 7.5, "org"),
        ("Desk, 6 reviewers", 4.5, "org")]

fig, ax = fl.figure(4.2, 3.4)
for i, (name, v, tok) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.barh(y, v, color=fl.FILL[tok], edgecolor=fl.C[tok], lw=0.75,
            hatch=fl.HATCH[0 if tok == "ops" else 1], height=0.6)
    ax.text(v * 1.15, y, f"{v:g} a minute", va="center", fontsize=9,
            color=fl.LABEL[tok])
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in reversed(rows)])
ax.set_xscale("log")
ax.set_xlim(1, 20000)
ax.set_xlabel("Items a minute (log scale)")
fl.save(fig)
