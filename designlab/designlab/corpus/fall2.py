"""The second fall: May 19, 2026, as it happened (Chapter 24).

A separate generator from corpus v0 and from fall1, so no earlier
digest moves. It covers one cancellation and the day after it.

At 10:52 a.m. CDT on Tuesday, May 19, Prairie Airways (XPA, a
fictional carrier) cancels its afternoon arrivals into Phoenix (event
CXL-0519). Lakeshore's fan-out touches 1,146 itineraries. Forty-one
of them belong to one corporate account: travelers booked by one
travel coordinator for a sales meeting in Phoenix. The pilot's legacy
note store holds one note for the coordinator, written by the
vendor extractor on November 19, 2025, from a chat about a December
trip: "prefers Denver". It has no scope, no subject, and an expiry
nobody enforced (180 days, May 18, 2026).

Tables:
    fall2_note        the legacy note, with what the pilot stored
    fall2_itins       the 1,146 itineraries the event touched
    fall2_options     same-carrier seats the planner could offer
    fall2_runs        one rebooking run per itinerary, as replayed
    fall2_history     earlier runs whose packet held a place note
    fall2_recovery    the 38 wrong-city travelers, put right

Counts are exact. Times are America/Chicago (CDT, -05:00) except the
note's creation time, which is CST (-06:00). Every record is invented.

    from corpus.fall2 import generate_fall2
    f = generate_fall2(2026)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

from common.rand import DEFAULT_SEED, seeded

FALL2_VERSION = "fall2-v1"
DAY = "2026-05-19"
NEXT = "2026-05-20"
CDT = timezone(timedelta(hours=-5))
CST = timezone(timedelta(hours=-6))
EVENT_ID = "CXL-0519"
CARRIER = "XPA"
CITY = "PHX"
WRONG = "DEN"

COORDINATOR = "CUS-024417"     # the booking customer for the account
ACCOUNT = "ACC-20417"          # a Milwaukee medical-device distributor
NOTE_ID = "MEM-60417"
NOTE_TEXT = "prefers Denver"
NOTE_QUOTE = ("For this trip we'd prefer Denver; the customer meeting "
              "moved there.")
NOTE_AT = datetime(2025, 11, 19, 14, 14, 9, tzinfo=CST)
NOTE_CONTACT = "CON-6610932"
RETENTION_DAYS = 180           # memory-retention-v1

N_ITINS = 1146
N_ACCOUNT = 41
N_WRONG = 38                   # rebooked to Denver within $250
N_HELD = 3                     # Denver proposals over $250, refused
N_REBOOKED = 1020              # act and notify, all paths
N_REFUND = 84                  # cancel-and-refund cards
N_REFUSAL = 42                 # to the refusal queue
FARE_LIMIT = 250.0             # rebook-v2


def hms(h: int, m: int, s: int = 0) -> int:
    return h * 3600 + m * 60 + s


CANCEL_AT = hms(10, 52)
FANOUT_START = hms(10, 58)
FANOUT_END = hms(13, 40)
ACCOUNT_FROM = hms(11, 31)     # the account's runs, in queue order
ACCOUNT_TO = hms(12, 18)
DETECT_AT = hms(14, 47)        # Keisha Navarro, refusal list
CALL_AT = hms(14, 58)          # Keisha calls Marcus Bell
KILL_AT = hms(15, 6)           # Ben Carter, tier one, rebook tool
SEARCH_AT = hms(15, 20)        # trail search on the note id
CAUSE_AT = hms(15, 40)         # Daniel Price finds the adapter
LAST_FIXED = hms(16, 31)       # Wednesday, last traveler in Phoenix

# Seats the planner could offer, same carrier. Times are departures,
# CDT; "day" is the departure day.
OPTIONS = (
    ("XPA1418", "ORD", "PHX", DAY, hms(13, 5), "canceled"),
    ("XPA1662", "MSP", "PHX", DAY, hms(13, 40), "canceled"),
    ("XPA0842", "ORD", "DEN", DAY, hms(16, 35), "scheduled"),
    ("XPA0916", "ORD", "DEN", DAY, hms(18, 50), "scheduled"),
    ("XPA0730", "MSP", "DEN", DAY, hms(17, 20), "scheduled"),
    ("XPA1422", "ORD", "PHX", NEXT, hms(7, 10), "scheduled"),
    ("XPA1430", "ORD", "PHX", NEXT, hms(12, 55), "scheduled"),
    ("XPA1668", "MSP", "PHX", NEXT, hms(8, 5), "scheduled"),
    ("XPA1676", "MSP", "PHX", NEXT, hms(13, 15), "scheduled"),
)
CANCELED = tuple(o[0] for o in OPTIONS if o[5] == "canceled")

# The account's 41 travelers: 26 from Chicago, 15 from Minneapolis.
# Denver legs chosen by the pilot: ORD 16 on the 4:35 p.m., 8 on the
# 6:50 p.m.; MSP 14 on the 5:20 p.m.; two ORD and one MSP over $250.
PLAN = (("ORD", "XPA1418", "XPA0842", 16), ("ORD", "XPA1418",
        "XPA0916", 8), ("ORD", "XPA1418", None, 2),
        ("MSP", "XPA1662", "XPA0730", 14), ("MSP", "XPA1662", None, 1))
CHECKED_IN = 7                 # on XPA0842 when the desk called
STOPPED_AT_GATE = 5
FLEW_TO_DENVER = 2
MORNING, AFTERNOON = 24, 12    # Wednesday Phoenix seats
GOODWILL_USD = 150.0
HOTEL_USD = 189.0              # one Denver night
ONWARD_USD = 214.0             # DEN to PHX, Wednesday

FALL2_TABLES = ("fall2_note", "fall2_itins", "fall2_options",
                "fall2_runs", "fall2_history", "fall2_recovery")


def clock(t: float) -> str:
    t = int(round(t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def iso(t: float, day: str = DAY) -> str:
    return f"{day}T{clock(t)}-05:00"


def note_expiry() -> datetime:
    return (NOTE_AT + timedelta(days=RETENTION_DAYS)).astimezone(CDT)


def _note() -> dict:
    return {"memory_id": NOTE_ID, "customer_id": COORDINATOR,
            "fact": NOTE_TEXT, "subject": None, "scope": None,
            "provenance": {"source": "vendor-extractor",
                           "contact_id": NOTE_CONTACT,
                           "quote": NOTE_QUOTE},
            "created_at": NOTE_AT.isoformat(),
            "expires_at": note_expiry().isoformat(),
            "expiry_enforced": False,
            "trip_named_in_quote": "December 2025 regional meeting"}


def _itin_id(n: int) -> str:
    return f"LTG-58{n:05d}"


def _times(rng, n: int, t0: int, t1: int) -> list[int]:
    return sorted(rng.randint(t0, t1) for _ in range(n))


def generate_fall2(seed: int = DEFAULT_SEED) -> dict[str, list[dict]]:
    rng = seeded(seed, "fall2", "itins")
    itins, runs = [], []
    n = 0
    # The account first, in the order the plan lists them.
    acct_times = iter(_times(rng, N_ACCOUNT, ACCOUNT_FROM, ACCOUNT_TO))
    for origin, flight, wrong, k in PLAN:
        for _ in range(k):
            n += 1
            iid = _itin_id(n)
            itins.append({"itinerary_id": iid, "customer_id": COORDINATOR,
                          "account": ACCOUNT, "traveler": f"T{n:02d}",
                          "origin": origin, "destination": CITY,
                          "segments": [flight], "carrier": CARRIER})
            t = next(acct_times)
            diff = (round(rng.uniform(0, 238), 2) if wrong
                    else round(rng.uniform(262, 318), 2))
            leg = wrong or ("XPA0842" if origin == "ORD" else "XPA0730")
            runs.append({
                "run_id": f"R-0519-{n:04d}", "itinerary_id": iid,
                "command_id": f"{EVENT_ID}:{iid}", "at": iso(t),
                "packet_notes": [NOTE_ID], "pinned_constraints":
                    [NOTE_TEXT], "proposal": leg,
                "proposal_dest": WRONG, "fare_diff_usd": diff,
                "disposition": "rebooked" if wrong else "refusal",
                "rationale": ("next PHX seats are tomorrow; DEN tonight "
                              "honors stated preference")})
    # Everyone else the event touched.
    rest = N_ITINS - N_ACCOUNT
    disp = (["rebooked"] * (N_REBOOKED - N_WRONG) + ["refund-card"] *
            N_REFUND + ["refusal"] * (N_REFUSAL - N_HELD))
    assert len(disp) == rest
    rng.shuffle(disp)
    other_notes = ("prefers aisle seat", "vegetarian meal",
                   "text me, don't call", "no red-eyes",
                   "prefers morning flights")
    for i, t in enumerate(_times(rng, rest, FANOUT_START, FANOUT_END)):
        n += 1
        iid = _itin_id(n)
        origin = rng.choice(("ORD", "MSP"))
        flight = "XPA1418" if origin == "ORD" else "XPA1662"
        cust = f"CUS-{rng.randint(30000, 99999):06d}"
        itins.append({"itinerary_id": iid, "customer_id": cust,
                      "account": None, "traveler": None,
                      "origin": origin, "destination": CITY,
                      "segments": [flight], "carrier": CARRIER})
        d = disp[i]
        notes = ([f"MEM-7{rng.randint(1000, 9999)}"]
                 if rng.random() < 0.28 else [])
        nxt = "XPA1422" if origin == "ORD" else "XPA1668"
        runs.append({
            "run_id": f"R-0519-{n:04d}", "itinerary_id": iid,
            "command_id": f"{EVENT_ID}:{iid}", "at": iso(t),
            "packet_notes": notes,
            "pinned_constraints": [rng.choice(other_notes)] if notes
            else [],
            "proposal": None if d == "refund-card" else nxt,
            "proposal_dest": None if d == "refund-card" else CITY,
            "fare_diff_usd": (round(rng.uniform(0, 240), 2)
                              if d == "rebooked" else
                              round(rng.uniform(255, 610), 2)
                              if d == "refusal" else 0.0),
            "disposition": d, "rationale": ""})
    options = [{"flight": f, "origin": o, "destination": d,
                "departs": iso(t, day), "status": s}
               for f, o, d, day, t, s in OPTIONS]
    history = _history(seeded(seed, "fall2", "history"))
    recovery = _recovery(seeded(seed, "fall2", "recovery"), runs)
    return {"fall2_note": [_note()], "fall2_itins": itins,
            "fall2_options": options, "fall2_runs": runs,
            "fall2_history": history, "fall2_recovery": recovery}


def _history(rng) -> list[dict]:
    """Earlier rebookings, November 3, 2025 to May 18, 2026, whose
    context packet carried a legacy note naming a place. None of them
    went to the wrong city; six carried the coordinator's note, in the
    notes block only (pinned compaction went live May 18)."""
    rows = []
    places = (("prefers Phoenix, not Mesa", "PHX"),
              ("flies home to Denver", "DEN"),
              ("prefers O'Hare to Midway", "ORD"),
              ("Boston office, not Cambridge", "BOS"))
    start = datetime(2025, 11, 24, tzinfo=CDT).toordinal()
    end = datetime(2026, 5, 15, tzinfo=CDT).toordinal()
    for k in range(14):
        day = datetime.fromordinal(rng.randint(start, end)).date()
        if k < 6:
            text, dest, cust, nid = (NOTE_TEXT, rng.choice(
                ("MKE", "PHX", "MSY", "DFW")), COORDINATOR, NOTE_ID)
        else:
            text, dest = rng.choice(places)
            cust = f"CUS-{rng.randint(30000, 99999):06d}"
            nid = f"MEM-7{rng.randint(1000, 9999)}"
        rows.append({"run_id": f"R-{day:%m%d}-{rng.randint(1, 9999):04d}",
                     "day": day.isoformat(), "customer_id": cust,
                     "note_id": nid, "note": text,
                     "itinerary_dest": dest, "final_dest": dest,
                     "note_slot": "memory", "pinned": False})
    return sorted(rows, key=lambda r: r["day"])


def _recovery(rng, runs: list[dict]) -> list[dict]:
    wrong = [r for r in runs if r["disposition"] == "rebooked"
             and r["proposal_dest"] == WRONG]
    assert len(wrong) == N_WRONG
    on_435 = [r for r in wrong if r["proposal"] == "XPA0842"]
    checked = set(r["run_id"] for r in rng.sample(on_435, CHECKED_IN))
    flew = set(rng.sample(sorted(checked), FLEW_TO_DENVER))
    contact = iter(_times(rng, N_WRONG, hms(15, 24), hms(17, 41)))
    seats = ["morning"] * MORNING + ["afternoon"] * AFTERNOON
    rng.shuffle(seats)
    seats = iter(seats)
    out = []
    for r in wrong:
        rid = r["run_id"]
        if rid in flew:
            route, arrive = "via-DEN", LAST_FIXED
            if len([o for o in out if o["route"] == "via-DEN"]) == 0:
                arrive = hms(16, 2)
        else:
            route = next(seats)
            arrive = (rng.randint(hms(10, 4), hms(11, 58))
                      if route == "morning" else
                      rng.randint(hms(15, 36), hms(16, 12)))
        out.append({
            "run_id": rid, "itinerary_id": r["itinerary_id"],
            "status_at_detection": "checked-in" if rid in checked
            else "not-traveled",
            "stopped_at_gate": rid in checked and rid not in flew,
            "contacted_at": iso(next(contact)), "route": route,
            "arrived_phx": iso(arrive, NEXT),
            "goodwill_usd": GOODWILL_USD,
            "hotel_usd": HOTEL_USD if rid in flew else 0.0,
            "onward_usd": ONWARD_USD if rid in flew else 0.0})
    return out


def fall2_digest(t: dict[str, list[dict]]) -> str:
    h = hashlib.sha256(FALL2_VERSION.encode())
    for name in FALL2_TABLES:
        h.update(name.encode())
        h.update(json.dumps(t[name], sort_keys=True).encode())
    return h.hexdigest()
