"""Stalled-loop detection, over persisted state.

Progress is a change in the persisted progress fields or a verified
outcome. The model's report of progress is not progress. A work step
is a model call or a proposed effect; after each one the detector
compares the state's progress digest with the one before it, counts
steps without a change (across runs, because the count is in the
state), and watches the last four digests for a two-state swing.
"""
from __future__ import annotations

from .state import progress_digest

NO_PROGRESS = 5
WINDOW = 4


def after_step(st: dict, before: str, verified: bool = False) -> str:
    """Update the counters in `st`; return '' or the stop's name."""
    now = progress_digest(st)
    if now == before and not verified:
        st["no_progress"] += 1
    else:
        st["no_progress"] = 0
    st["recent"] = (st["recent"] + [now])[-WINDOW:]
    r = st["recent"]
    if st["no_progress"] >= NO_PROGRESS:
        return "no-progress"
    if len(r) == WINDOW and r[0] == r[2] and r[1] == r[3] \
            and r[0] != r[1]:
        return "oscillation"
    return ""
