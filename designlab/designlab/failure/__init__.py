"""designlab.failure: failure modes, retries by plane, breakers,
degraded modes, and reconciliation against settlement (Chapter 12).

Offline. Built on effects (keys, ledger, executor, guard), the fall-1
corpus, and the Chapter 7 supplier simulators. No model is called.
"""
from .breaker import Breaker
from .catalog import CATALOG, by_plane
from .reconcile import Report, reconcile, ratio_alert, interval_scan
from .retry import POLICIES, amplification, backoff

__all__ = ["Breaker", "CATALOG", "by_plane", "Report", "reconcile",
           "ratio_alert", "interval_scan", "POLICIES", "amplification",
           "backoff"]
