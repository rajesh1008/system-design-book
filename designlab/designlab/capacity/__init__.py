"""The Capacity Model (Chapter 10): estimate, budget, and surge.

Fitted to 90 days of Lakeshore pilot traces (corpus.traces), December
1, 2025, to February 28, 2026. Standard library only, offline.

    from capacity import estimate, budget, surge
"""
from .estimate import Fit, estimate, fit_traces
from .budget import PLANE_BUDGET, Design, check_budget, predict, replay
from .surge import size_surge

__all__ = ["Fit", "estimate", "fit_traces", "PLANE_BUDGET", "Design",
           "check_budget", "predict", "replay", "size_surge"]
