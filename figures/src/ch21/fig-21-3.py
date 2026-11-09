"""Figure 21.3  Pinned facts compaction must keep.

Reading order: one row per kind of fact, top to bottom, with the rule
the compactor follows on the right. Rows with a solid tab are
commitments pinned verbatim: the pending approval APR-48213, its amount
of $412.80, its idempotency key, and the customer's constraint. Rows with
a dotted tab are references the trail can confirm. The
hatched row is the only thing the summary may phrase in its own words.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [("Pending approval", "Pin", "policy"),
        ("Amount", "Pin", "policy"),
        ("Idempotency key", "Pin", "policy"),
        ("Customer constraint", "Pin verbatim", "policy"),
        ("Closed approval", "Keep as closed", "evidence"),
        ("Tool results", "Clear to a handle", "evidence"),
        ("Reasoning", "Summarize", "model")]

fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in ((0.7, "Fact"), (6.0, "Rule")):
    ax.text(x, n + 0.4, h, fontsize=10, fontweight="bold", va="center")
for i, (kind, rule, role) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0, y + 0.06), 10, 0.88, facecolor="white",
                           edgecolor=fl.C[role], lw=0.9))
    ax.add_patch(Rectangle((0, y + 0.06), 0.45, 0.88, facecolor=fl.C[role],
                           edgecolor=fl.C[role], lw=0.9,
                           hatch={"policy": "", "evidence": "...",
                                  "model": "///"}[role]))
    ax.text(0.7, y + 0.5, kind, fontsize=10, va="center", color=fl.INK)
    ax.text(6.0, y + 0.5, rule, fontsize=10, va="center", color=fl.INK)
fl.save(fig)
