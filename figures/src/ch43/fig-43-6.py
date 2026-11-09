"""Figure 43.6  Card-network rules in the permission plane.

Reading order: one row per rule the bank's rules table checks before
the policy engine grants a filing, top to bottom: the rule and the
clock the table enforces. The last row is the consumer's own clock
under Regulation E. Network rules from the research note verified
November 2, 2026; Regulation E 1005.11 verified November 9, 2026. From
designs/data/bank-payments.toml, obligations network-rules and reg-e.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "04-code" / "designlab"))
sys.path.insert(0, str(HERE))
import figlib as fl  # noqa: E402
from _table import table  # noqa: E402

rows = (("Visa 12.6", "Duplicate", "By day 120"),
        ("Visa 13.6", "Credit not processed", "Day 15 to 120"),
        ("Mastercard 4834", "Duplicate", "By day 90"),
        ("Mastercard 4853", "Credit not processed", "Credit reference"),
        ("Regulation E", "Error claim", "10 or 45 days"))
toks = ["policy"] * 4 + ["evidence"]
fig, ax = table(rows, ("Rule", "Claim", "Table checks"),
                (0.0, 1.75, 3.55), toks=toks, h=3.0)
fl.save(fig)
