"""Figure 3.9  The shortlist decision table.

Reading order: two blocks, runtimes then frameworks, each ranked by
score top to bottom. Score = gap points minus half a point per step of
lock-in above 1. Generated from map.yaml by map.shortlist on 2026-11-02.
"""
import sys
from pathlib import Path

import figlib as fl
from matplotlib.patches import Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "04-code" / "designlab"))
from map.model import load  # noqa: E402
from map.shortlist import rank, shortlist  # noqa: E402

m = load()
picks = shortlist(m)
short = {"Microsoft Foundry Agent Service": "Foundry Agent Service",
         "Gemini Enterprise Agent Runtime": "Gemini Agent Runtime",
         "Amazon Bedrock AgentCore": "AgentCore",
         "Microsoft Agent Framework": "Agent Framework"}
rows = []
for cat, title in (("runtime", "Hosted runtimes"), ("framework", "Frameworks")):
    rows.append(("head", title, None, None))
    for s in rank(m, cat):
        chosen = any(s.option.id == p.option.id for p in picks[cat])
        why = "shortlist" if chosen else (s.reason.replace("status ", "") or "lower score")
        rows.append(("row", short.get(s.option.name, s.option.name), s.score, (chosen, why)))
fig, ax = fl.figure(4.5, 4.6)
n = len(rows)
ax.set_xlim(0, 10.6)
ax.set_ylim(0, n + 0.2)
ax.axis("off")
for i, (kind, name, sc, extra) in enumerate(rows):
    y = n - i - 0.5
    if kind == "head":
        ax.text(0.0, y, name, va="center", fontweight="bold", color=fl.LABEL["org"])
        ax.text(5.5, y, "Score", va="center", ha="center", fontweight="bold")
        continue
    chosen, why = extra
    ax.text(0.3, y, name, va="center")
    ax.text(5.5, y, f"{sc:.1f}", va="center", ha="center", **fl.mono("0"))
    tok = "verified" if chosen else ("policy" if why in ("beta", "pre-1.0") else "org")
    ax.add_patch(Rectangle((6.8, y - 0.36), 3.7, 0.72,
                           facecolor=fl.C[tok] if chosen else "white",
                           edgecolor=fl.C[tok], lw=fl.STROKE["data"],
                           linestyle="-" if chosen else "--"))
    ax.text(8.65, y, why, va="center", ha="center",
            color="white" if chosen else fl.LABEL[tok])
fl.save(fig)
