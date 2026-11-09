"""Figure 30.4  Hosted runtimes: what each hosts.

Reading order: one row per product, top to bottom; the unit of work,
where state is kept, and what else the vendor sells beside it. From
vendor documentation read in June 2026 and re-read November 2, 2026.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("LangSmith\nDeployment", "Threads,\ndurable runs", "Registry,\nA2A, MCP", "ops"),
        ("AgentCore\nRuntime", "Session per\nmicroVM, 8 h", "Gateway,\nPolicy, Memory", "policy"),
        ("Gemini Agent\nRuntime", "Container,\nsessions", "Memory banks,\nsandboxes", "evidence"),
        ("Claude Managed\nAgents", "Session, its\nown harness", "Skills, MCP,\nschedules", "ops"))
cols = (0.0, 1.55, 3.05)
heads = ("Product", "Unit of work", "Also sells")
fig, ax = fl.figure(4.5, 3.0)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (a, b, c, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, (a, b, c)):
        ax.text(x + 0.05, y + 0.5, t, va="center", fontsize=9,
                color=fl.INK, linespacing=0.95,
                fontweight="bold" if x == cols[0] else None)
fl.save(fig)
