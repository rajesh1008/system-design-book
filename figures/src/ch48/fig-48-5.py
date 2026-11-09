"""Figure 48.5  The role in five years.

Reading order: one row per kind of work the agent platform team did
in 2026, top to bottom from the work that moves to models and
runtimes to the work that stays and grows. The middle column is the
team's 2026 share of time; the right column is the dated prediction
for 2031. Predictions, recorded in DR-48.1, not measurements.
Lakeshore figures are illustrative.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = [("Prompt and tool glue", "High", "Mostly gone"),
        ("Hosting and scaling", "Medium", "Rented"),
        ("Evals and golden sets", "Medium", "Same, owned"),
        ("Permission rules", "Low", "Grows"),
        ("Verifiers and records", "Medium", "Grows"),
        ("Pricing outcomes", "Low", "Grows"),
        ("Reading incidents", "Medium", "Same")]
toks = ["org"] * 2 + ["ops"] + ["verified"] * 3 + ["ops"]
fig, ax = table(rows, ("Work", "2026", "2031 bet"), (0.0, 2.55, 3.55),
                width=5.0, toks=toks, h=3.2)
fl.save(fig)
