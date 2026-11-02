"""Figure 3.8  Gap coverage heat grid, 31 options by 5 gaps.

Reading order: rows are the 31 options grouped by category, top to
bottom; columns are G1 to G5. Generated from 04-code/designlab/map/
map.yaml. Solid green with 2 = closes, hatched with 1 = partial,
blank = none. The G4 and G5 columns have no solid cell.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from map.model import GAP_IDS, load  # noqa: E402

m = load()
rows = []
for cat, opts in m.by_category().items():
    rows.append(("cat", m.categories[cat]))
    rows.extend(("opt", o) for o in opts)
short = {"Microsoft Foundry Agent Service": "Foundry Agent Service",
         "Gemini Enterprise Agent Runtime": "Gemini Agent Runtime",
         "Amazon Bedrock AgentCore": "AgentCore",
         "OpenTelemetry GenAI conventions": "OTel GenAI conventions",
         "Microsoft Agent Framework": "Agent Framework",
         "Agentic Commerce Protocol (ACP)": "ACP",
         "Agent Payments Protocol (AP2)": "AP2",
         "Model Context Protocol": "MCP", "Agent2Agent (A2A)": "A2A"}
fig, ax = fl.figure(4.5, 8.4)
n = len(rows)
ax.set_xlim(0, 10)
ax.set_ylim(-0.6, n + 1)
ax.axis("off")
x0, w = 5.0, 1.0
for j, g in enumerate(GAP_IDS):
    ax.text(x0 + j * w + w / 2, n + 0.4, g, ha="center", fontweight="bold")
for i, (kind, item) in enumerate(rows):
    y = n - i - 0.5
    if kind == "cat":
        ax.text(0.0, y, item, va="center", fontweight="bold", color=fl.LABEL["org"])
        continue
    ax.text(0.3, y, short.get(item.name, item.name), va="center", fontsize=9.5)
    for j, g in enumerate(GAP_IDS):
        code = item.gaps[g]
        x = x0 + j * w
        if code == "closes":
            face, hatch, txt = fl.C["verified"], "", "2"
        elif code == "partial":
            face, hatch, txt = fl.FILL["verified"], "///", "1"
        else:
            face, hatch, txt = "white", "", ""
        ax.add_patch(Rectangle((x + 0.06, y - 0.42), w - 0.12, 0.84, facecolor=face,
                               edgecolor=fl.GREY_LIGHT if code == "none" else fl.C["verified"],
                               lw=0.5, hatch=hatch))
        if txt:
            ax.text(x + w / 2, y, txt, ha="center", va="center", fontsize=9,
                    color="white" if code == "closes" else fl.LABEL["verified"],
                    bbox=None if code == "closes" else dict(facecolor="white", edgecolor="none", pad=0.5))
ax.add_patch(Rectangle((x0 + 3 * w, -0.5), 2 * w, n + 0.05, fill=False,
                       edgecolor=fl.C["fail"], lw=fl.STROKE["control"], linestyle="--"))
ax.text(x0 + 4 * w, -0.35, "no option closes", ha="center", va="top",
        color=fl.LABEL["fail"], fontsize=9.5)
fl.save(fig)
