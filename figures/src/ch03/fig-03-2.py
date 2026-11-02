"""Figure 3.2  Frameworks and SDKs by what they decide for you.

Reading order: one row per framework, top to bottom; columns left to
right: the loop shape it gives you, where its permission hook runs, and
its version line. Versions read from release pages on 2026-11-02.
"""
import figlib as fl
from matplotlib.patches import Rectangle

rows = [
    ("LangGraph", "graph", "1.2", True),
    ("OpenAI Agents SDK", "handoffs", "0.24", False),
    ("Claude Agent SDK", "agent loop", "0.2", False),
    ("Agent Framework", "workflows", "1.24", True),
    ("Google ADK", "workflows", "2.13", True),
    ("CrewAI", "crews, flows", "1.15", True),
    ("Strands Agents", "swarm, graph", "1.x", True),
]
fig, ax = fl.figure(4.5, 3.6)
n = len(rows)
ax.set_xlim(0, 10.6)
ax.set_ylim(0, n + 1)
ax.axis("off")
cols = ((0.1, "Framework"), (4.0, "Loop shape"), (6.6, "Permission"),
        (9.3, "Version"))
for x, text in cols:
    ax.text(x, n + 0.5, text, fontweight="bold", va="center")
for i, (name, shape, ver, ga) in enumerate(rows):
    y = n - i - 0.5
    ax.text(0.1, y, name, va="center", color=fl.LABEL["org"])
    ax.add_patch(Rectangle((3.9, y - 0.34), 2.5, 0.68, facecolor=fl.FILL["ops"],
                           edgecolor=fl.C["ops"], lw=fl.STROKE["data"]))
    ax.text(5.15, y, shape, va="center", ha="center", color=fl.LABEL["ops"],
            fontsize=9.5)
    ax.text(6.6, y, "in process", va="center", fontstyle="italic")
    tok = "model" if ga else "org"
    ax.add_patch(Rectangle((9.2, y - 0.34), 1.3, 0.68, facecolor=fl.FILL[tok],
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"],
                           hatch="" if ga else "///"))
    ax.text(9.85, y, ver, va="center", ha="center",
            color=fl.TEXT_ON[tok] if ga else fl.LABEL["org"],
            bbox=None if ga else dict(facecolor="white", edgecolor="none", pad=1))
    ax.plot([0, 10.6], [y - 0.5, y - 0.5], color=fl.GREY_LIGHT, lw=0.5,
            linestyle="-", marker="")
fl.save(fig)
