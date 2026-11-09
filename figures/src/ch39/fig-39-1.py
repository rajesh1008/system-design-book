"""Figure 39.1  What changes behavior.

Reading order: one row per kind of change, top to bottom: prompts,
models, tools, the harness, the policy bundle, and memory; a Lakeshore
example of each, and whether June's rule (a code deploy) would have
counted it. The kind's color repeats its name; the last column says
the same in words. From release.bundle and release.log (Lakeshore
figures are illustrative).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from release import log as L  # noqa: E402

c = L.counts()
by = c["by_kind"]
rows = [("Prompt", "refund-reason@1.4", "Repo file only", "model"),
        ("Model", "Mid snapshot", "Student only", "model"),
        ("Tool", "payments 3.1", "Yes", "ops"),
        ("Harness", "Step budget", "Code only", "ops"),
        ("Policy", "pb-2026.08.10", "No", "policy"),
        ("Memory", "Schema 3", "Extracts only", "knowledge")]
heads = ("Kind", "Example", "June's rule", "Count")
cols = (0.0, 1.05, 2.75, 4.35)
fig, ax = fl.figure(4.5, 3.2)
n = len(rows)
ax.set_xlim(0, 5.1)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=9.5,
            fontweight="bold", color=fl.INK)
for i, (kind, ex, june, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 5.1, 0.88,
                           facecolor=("white" if tok == "model"
                                      else fl.FILL[tok]),
                           edgecolor=fl.C[tok],
                           lw=1.5 if tok == "model" else 0.75))
    ax.text(0.05, y + 0.5, kind, va="center", fontsize=9,
            fontweight="bold", color=fl.LABEL[tok])
    ax.text(cols[1] + 0.05, y + 0.5, ex, va="center", fontsize=9,
            color=fl.INK)
    ax.text(cols[2] + 0.05, y + 0.5, june, va="center", fontsize=9,
            color=fl.INK)
    ax.text(cols[3] + 0.05, y + 0.5, str(by[kind.lower()]), va="center",
            fontsize=9, color=fl.INK)
fl.save(fig)
