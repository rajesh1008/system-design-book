"""Figure 40.8  What the sibling owns.

Reading order: one row per topic, top to bottom: what this chapter
covers and what the companion volume on platform engineering covers at
depth (Lakeshore figures are illustrative).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("Platform team", "What it owns", "Team design"),
        ("Portal", "One manifest", "Portals, catalogs"),
        ("Golden paths", "One for agents", "Many, and upkeep"),
        ("Adoption", "One onboarding", "Measuring it"),
        ("Funding", "Fixed plus marginal", "Budgets, showback"))
fig = table(rows, ("Topic", "This chapter", "Companion volume"),
            (0.0, 1.35, 3.05), toks=["org"] * 5)
fl.save(fig)
