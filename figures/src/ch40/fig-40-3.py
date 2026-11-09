"""Figure 40.3  What to leave to teams.

Reading order: one row per thing a team owns, top to bottom, with the
platform's one line for it. From agentplatform.template, TEAM_OWNED
and PLATFORM_OWNED (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("Prompts", "No limits inside them"),
        ("Retrieval", "Sources named, cost charged"),
        ("Model choice", "Pinned, through the gateway"),
        ("Tool servers", "Registered and reviewed"),
        ("Golden tasks", "Thirty or more, run here"),
        ("Result", "An owner outside the team"))
fig = table(rows, ("Team owns", "Platform's line"), (0.0, 1.55),
            toks=["org"] * 6, h=3.2)
fl.save(fig)
