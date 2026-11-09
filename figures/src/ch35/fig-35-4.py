"""Figure 35.4  Semantic conventions mapped to the chain.

Reading order: one row per link of the chain, top to bottom; the span
that records the link and the attributes it carries. Names starting
gen_ai come from the OpenTelemetry GenAI conventions (status
Development, read November 2, 2026); names starting lakeshore are the
ones the conventions do not define. From tracing.conventions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
import figlib as fl  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

rows = (("Output", "chat", "gen_ai.usage.*\nlakeshore.cost.usd", "model"),
        ("Proposal", "chat", "lakeshore.args.sha256\nlakeshore.io.ref", "model"),
        ("Permission", "policy", "lakeshore.policy.verdict\nlakeshore.permit.id", "policy"),
        ("Execution", "execute_tool", "gen_ai.tool.call.id\nlakeshore.trail.hash", "ops"),
        ("Verified\noutcome", "verify", "lakeshore.verify.result\nlakeshore.verify.by", "verified"),
        ("Business\nresult", "invoke_agent", "gen_ai.conversation.id\nlakeshore.outcome", "evidence"))
cols = (0.0, 1.0, 2.3)
heads = ("Link", "Span", "Attributes")
fig, ax = fl.figure(4.8, 3.9)
n = len(rows)
ax.set_xlim(0, 4.95)
ax.set_ylim(-0.1, n + 0.9)
ax.axis("off")
for x, h in zip(cols, heads):
    ax.text(x + 0.05, n + 0.45, h, va="center", fontsize=10,
            fontweight="bold", color=fl.INK)
for i, (*cells, tok) in enumerate(rows):
    y = n - 1 - i
    ax.add_patch(Rectangle((0.0, y + 0.06), 4.95, 0.88,
                           facecolor="white", edgecolor=fl.GREY_LIGHT,
                           lw=0.75))
    ax.add_patch(Rectangle((0.0, y + 0.06), cols[1] - 0.05, 0.88,
                           facecolor=fl.FILL[tok], edgecolor=fl.C[tok],
                           lw=0.75))
    for x, t in zip(cols, cells):
        ax.text(x + 0.05, y + 0.5, t, va="center",
                fontsize=9,
                color="white" if (tok == "model" and x == cols[0]) else fl.INK,
                family="monospace" if x != cols[0] else None,
                fontweight="bold" if x == cols[0] else None)
fl.save(fig)
