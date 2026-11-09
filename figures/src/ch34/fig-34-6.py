"""Figure 34.6  Error analysis by failure class.

Reading order: one bar per cluster of June disagreements, largest
first, labeled with the class and whether the agent was wrong.
From evals.demo --part harvest. Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402

rows = (("Approver edited:\nsplit payment", 99, "fail", "agent wrong"),
        ("Contacted again:\nany class", 92, "ops", "no task"),
        ("Hand-off after error:\ntwo timeouts", 33, "ops", "agent right"),
        ("Reviewer rejected:\nhotel email", 1, "fail", "agent wrong"))
fig, ax = fl.figure(4.5, 3.3)
for i, (lab, n, tok, v) in enumerate(rows):
    y = 3 - i
    ax.barh(y, n, color=fl.FILL[tok], edgecolor=fl.C[tok], lw=0.75,
            hatch=fl.HATCH[1] if tok == "fail" else fl.HATCH[0], height=0.6)
    ax.text(n + 3, y, f"{n}, {v}", va="center", fontsize=9.5, color=fl.INK)
ax.set_yticks([3, 2, 1, 0])
ax.set_yticklabels([r[0] for r in rows], fontsize=9.5)
ax.set_xlim(0, 150)
ax.set_xlabel("June traces in the cluster")
fl.save(fig)
