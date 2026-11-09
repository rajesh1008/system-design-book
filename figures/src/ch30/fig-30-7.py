"""Figure 30.7  The comparison grid.

Reading order: one row per option, best first; points by plane out of
the plane's maximum, then the total out of 44. Read from
runtimes/grid.yaml through runtimes.grid, as of June 19, 2026.
"""
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parents[3] / "04-code" / "designlab"
sys.path.insert(0, str(LAB))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from runtimes import grid as G  # noqa: E402

NAMES = {"langsmith-deployment": "LangSmith", "agentcore": "AgentCore",
         "gemini-agent-runtime": "Gemini", "langgraph": "LangGraph self",
         "ms-agent-framework": "MAF self"}
g = G.load()
heads = ("Option", "Act\n/12", "Ctl\n/12", "Knw\n/8", "Trl\n/8",
         "Prt\n/4", "Total")
cols = (0.0, 1.45, 1.98, 2.51, 3.04, 3.57, 4.1)
fig, ax = fl.figure(4.5, 3.0)
rows = G.rank(g)
n = len(rows)
ax.set_xlim(0, 4.6)
ax.set_ylim(-0.1, n + 1.1)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.55, h, va="center", fontsize=9,
            fontweight="bold", color=fl.INK)
for i, (o, t, _) in enumerate(rows):
    y = n - 1 - i
    tok = "org" if i == 0 else ("policy" if o.kind == "framework" else "ops")
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.6, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    p = G.by_plane(g, o)
    vals = [NAMES[o.id]] + [str(p[k]) for k in G.PLANES] + [f"{t:g}"]
    for x, v in zip(cols, vals):
        ax.text(x + 0.05, y + 0.5, v, va="center", fontsize=9,
                color=fl.INK, fontweight="bold" if x in (0.0, 4.1) else None)
fl.save(fig)
