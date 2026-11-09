"""Go-live and the fall (Chapter 44): Lakeshore's storm day of
Thursday, September 10, 2026, replayed from synthetic records.

Modules:
    day      the 41,000 changes of the storm window, and the day's
             other arrivals, as seeded records
    desk     the approval queue: approvers, order, latency, misses
    budget   the fleet-day model budget under load
    replay   one scenario run end to end, and the named scenarios
    record   the incident record as a trace (tracing.spans)
    ramp     the ramp by task type, and a ramp by traffic share
    pilot    the pilot and its numbers
    review   recovery measured, the three designs, the fall card
    demo     everything the chapter pastes

Offline and deterministic. No model call and no key. Lakeshore
figures are illustrative.
"""
from .day import STORM_CHANGES, generate
from .replay import SCENARIOS, Scenario, run

__all__ = ["STORM_CHANGES", "generate", "SCENARIOS", "Scenario", "run"]
