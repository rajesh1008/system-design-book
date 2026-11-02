"""A loop declared as data: the seven properties, one field each.

The linter reads this, not the code. A loop that cannot fill in a
field has not been designed yet, whatever its code does. Two loops
went live at Lakeshore in June 2026: the fare watch (June 12; this
spec is its June 19 redesign, 1.1.0) and the waiver watch (June 25).
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import copy

FARE_WATCH = {
    "loop": "fare-watch",
    "version": "1.1.0",
    "actor": "loop:fare-watch",
    "trigger": {
        "kinds": ["schedule", "event"],
        "schedule": "hourly, spread across the hour",
        "event": "fare filing published for a watched flight",
        "run_key": ["watch", "hour", "filing_digest"],
        "max_runs_per_watch_hour": 2,
    },
    "stops": [
        {"id": "checked", "check": "trail",
         "test": "an allowed offers_search for this watch this run"},
        {"id": "outcome", "check": "verifier",
         "test": "voucher in the ledger at the re-derived amount"},
        {"id": "no-progress", "check": "state",
         "test": "5 work steps with no change in persisted state"},
        {"id": "oscillation", "check": "state",
         "test": "state returns to the one two steps back, twice"},
        {"id": "budget", "check": "enforcer",
         "test": "run, loop-day or loops-day budget refuses"},
        {"id": "expired", "check": "state",
         "test": "departure passed or watch older than 30 days"},
    ],
    "state": {
        "store": "run_store",
        "schema": 2,
        "key": "watch",
        "fields": ["floor_usd", "last_digest", "verdicts",
                   "vouchers_usd", "no_progress", "recent",
                   "status"],
        "progress": ["floor_usd", "last_digest", "verdicts",
                     "vouchers_usd"],
    },
    "verify": {
        "verifier": "verifier:fare-watch",
        "reads": ["gateway trail", "offers_search, own identity",
                  "voucher ledger"],
        "effects": [],
        "sample": 0.02,
        "on_mismatch": "page; hour red; effects hold",
    },
    "budget": {
        "enforced_by": "budget enforcer",
        "run_usd": 0.05, "run_steps": 6,
        "loop_day_usd": 20.00, "loops_day_usd": 40.00,
        "alert": 0.80,
    },
    "change": {
        "grant": ["offers_search", "voucher_issue", "customer_notify"],
        "effects": {
            "voucher_issue": {"policy": "vouchers-v1",
                              "per_action_usd": 100.00,
                              "per_day_usd": 5000.00,
                              "audit_sample": 0.05},
            "customer_notify": {"template": "update",
                                "per_watch_day": 1},
        },
    },
    "human": {
        "owner": "Ben Carter",
        "pages": ["verifier mismatch on an effect",
                  "loop-day budget at 80%",
                  "voucher budget at 80%"],
        "morning_queue": ["stall", "read mismatch, no effect",
                          "budget refusal"],
        "hand_off": "agent desk, Marcus Bell's team",
        "kill_switch": ["watch", "loop effects at the gateway",
                        "loop off"],
        "review": "Monday on-call review, loop card",
    },
}

WAIVER_WATCH = {
    "loop": "waiver-watch",
    "version": "1.0.0",
    "actor": "loop:waiver-watch",
    "trigger": {
        "kinds": ["event", "schedule"],
        "schedule": "every six hours",
        "event": "carrier waiver notice published",
        "run_key": ["notice_id", "notice_digest"],
        "max_runs_per_watch_hour": 1,
    },
    "stops": [
        {"id": "read", "check": "trail",
         "test": "an allowed notice_read for the notice"},
        {"id": "outcome", "check": "verifier",
         "test": "one delivery receipt per affected itinerary"},
        {"id": "no-progress", "check": "state",
         "test": "5 work steps with no change in persisted state"},
        {"id": "oscillation", "check": "state",
         "test": "state returns to the one two steps back, twice"},
        {"id": "budget", "check": "enforcer",
         "test": "run, loop-day or loops-day budget refuses"},
    ],
    "state": {
        "store": "run_store", "schema": 2, "key": "notice",
        "fields": ["affected", "notified", "no_progress", "recent"],
        "progress": ["affected", "notified"],
    },
    "verify": {
        "verifier": "verifier:waiver-watch",
        "reads": ["gateway trail", "messaging delivery receipts"],
        "effects": [], "sample": 1.0,
        "on_mismatch": "page; notices hold",
    },
    "budget": {
        "enforced_by": "budget enforcer",
        "run_usd": 0.25, "run_steps": 12,
        "loop_day_usd": 10.00, "loops_day_usd": 40.00,
        "alert": 0.80,
    },
    "change": {
        "grant": ["notice_read", "booking_read", "customer_notify"],
        "effects": {
            "customer_notify": {"template": "update",
                                "per_itinerary_notice": 1,
                                "per_day": 2000},
        },
    },
    "human": {
        "owner": "Ben Carter",
        "pages": ["verifier mismatch on an effect",
                  "loop-day budget at 80%"],
        "morning_queue": ["stall", "budget refusal"],
        "hand_off": "agent desk, Marcus Bell's team",
        "kill_switch": ["notice", "loop effects at the gateway",
                        "loop off"],
        "review": "Monday on-call review, loop card",
    },
}

LIVE = (FARE_WATCH, WAIVER_WATCH)


def fare_watch_v0() -> dict:
    """The fare watch as it went live on Friday, June 12, 2026: the
    run ends when the model reports the hour done, the model checks
    its own work, the state lives in the worker, and the run budget
    is a counter in the loop."""
    s = copy.deepcopy(FARE_WATCH)
    s["version"] = "1.0.0"
    s["trigger"] = {"kinds": ["schedule"], "schedule": "hourly",
                    "max_runs_per_watch_hour": 1}
    s["stops"] = [{"id": "hour-done", "check": "model",
                   "test": "the model reports all fares checked"},
                  {"id": "step-cap", "check": "loop",
                   "test": "24 steps, counted in the loop"}]
    s["state"] = {"store": "worker memory", "key": "watch",
                  "fields": ["floor_usd"], "progress": []}
    s["verify"] = {"verifier": "loop:fare-watch",
                   "reads": ["the model's hourly report"],
                   "effects": [], "sample": 0.0}
    s["budget"] = {"enforced_by": "loop", "run_steps": 24}
    s["human"] = {"owner": "Ben Carter",
                  "pages": ["no report for two hours"],
                  "review": "dashboard"}
    return s


def model_stop(spec: dict) -> dict:
    """Failure injection: the loop's stop is the model's judgment."""
    s = copy.deepcopy(spec)
    s["loop"] += "+model-stop"
    s["stops"] = [x for x in s["stops"]
                  if x["id"] not in ("no-progress", "oscillation")]
    s["stops"].insert(0, {"id": "agent-done", "check": "model",
                          "test": "the agent says the watch is done"})
    return s


def no_state(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    s["loop"] += "+no-state"
    s["state"] = {"store": "worker memory", "key": "watch",
                  "fields": s["state"]["fields"], "progress": []}
    return s


def self_verify(spec: dict) -> dict:
    s = copy.deepcopy(spec)
    s["loop"] += "+self-verify"
    s["verify"] = dict(s["verify"], verifier=s["actor"],
                       reads=["the actor's report"])
    return s


def day_budget(spec: dict, usd: float) -> dict:
    s = copy.deepcopy(spec)
    s["loop"] += f"+${usd:g}-a-day"
    s["budget"] = dict(s["budget"], loop_day_usd=usd)
    return s
