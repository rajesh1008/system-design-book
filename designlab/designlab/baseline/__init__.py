"""designlab.baseline: Lakeshore before any agent design (Chapter 4).

Volume, mix, cost decomposition, refund error and the honest
automation rate, read from the operations tables in `corpus.ops`.
Offline only; no model calls.
"""
from .volume import count_changes, naive_count
from .cost import decompose
from .errors import refund_error, dot_clock
from .autonomy import (HONEST, VENDOR, Definition, automation_rate,
                       metric_test, autonomy_share)
from .scoreboard import baseline_row

__all__ = ["count_changes", "naive_count", "decompose", "refund_error",
           "dot_clock", "HONEST", "VENDOR", "Definition",
           "automation_rate", "metric_test", "autonomy_share",
           "baseline_row"]
