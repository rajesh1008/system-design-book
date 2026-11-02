"""Figure 3.3  Hosted runtimes: what each hosts and what it leaves.

Reading order: one row per runtime; columns left to right: sessions,
a policy decision outside the agent's code, traces and evaluations, and
the effect ledger. Solid = hosted, hatched = partial, white = yours.
Read from vendor documentation on 2026-11-02.
"""
import figlib as fl
from matplotlib.patches import Rectangle

H, P, Y = "hosted", "partial", "yours"
rows = [
    ("AgentCore", H, H, H, Y),
    ("Foundry Agent Service", H, P, H, Y),
    ("Gemini Agent Runtime", H, H, H, Y),
    ("Claude Managed Agents", H, P, P, Y),
    ("LangSmith Deployment", H, P, H, Y),
]
cols = [("Sessions", "ops"), ("Policy", "policy"), ("Traces", "evidence"),
        ("Ledger", "evidence")]
fig, ax = fl.figure(4.8, 3.2)
n = len(rows)
ax.set_xlim(0, 12.6)
ax.set_ylim(0, n + 1)
ax.axis("off")
x0, w = 5.7, 1.72
ax.text(0.1, n + 0.5, "Runtime", fontweight="bold", va="center")
for j, (head, _) in enumerate(cols):
    ax.text(x0 + j * w + w / 2, n + 0.5, head, fontweight="bold",
            va="center", ha="center")
for i, row in enumerate(rows):
    y = n - i - 0.5
    ax.text(0.1, y, row[0], va="center", color=fl.LABEL["org"])
    for j, (val, (_, tok)) in enumerate(zip(row[1:], cols)):
        x = x0 + j * w
        fill = {H: fl.FILL[tok], P: "white", Y: "white"}[val]
        ax.add_patch(Rectangle((x + 0.08, y - 0.34), w - 0.16, 0.68,
                               facecolor=fill, edgecolor=fl.C[tok if val != Y else "org"],
                               lw=fl.STROKE["data"], hatch="///" if val == P else "",
                               linestyle="--" if val == Y else "-"))
        ax.text(x + w / 2, y, val, va="center", ha="center",
                color=fl.LABEL[tok if val != Y else "org"], fontsize=9.5,
                bbox=dict(facecolor="white", edgecolor="none", pad=0.8) if val == P else None)
fl.save(fig)
