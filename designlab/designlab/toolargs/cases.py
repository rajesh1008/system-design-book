"""Calls to check: a seeded synthetic stream and twenty live cases.

The synthetic stream stands in for two weeks of effect-tool calls. Each
call has the arguments a careful clerk would write (`truth`) and, for a
small share, a fault: one argument that is well formed and wrong in the
world. `SimProposer` plays the model. It always emits schema-valid
arguments (strict tool use guarantees shape), and when a call is
rejected it repairs with probabilities that depend on whether it was
told what was wrong. The probabilities are illustrative; the live cases
check the same layer against the real small model.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

from common.rand import seeded

from .world import World, money

FAULTS = (            # (reason, weight)
    ("ticket_not_on_itinerary", 0.28),
    ("fare_quote_mismatch", 0.22),
    ("amount_above_fare_left", 0.17),
    ("passenger_not_on_ticket", 0.14),
    ("flight_not_on_route", 0.09),
    ("flight_canceled", 0.05),
    ("ticket_unknown", 0.05),
)


@dataclass
class Case:
    n: int
    session: str
    tool: str
    truth: dict
    fault: str | None = None
    bad: dict | None = None
    latent: str | None = None          # wrong in a way no rule checks yet
    alts: list = field(default_factory=list)


class Stream:
    def __init__(self, world: World, seed: int = 16,
                 fault_rate: float = 0.0232, latent_rate: float = 0.001):
        self.w, self.rng = world, seeded(seed, "toolargs", "stream")
        self.fault_rate, self.latent_rate = fault_rate, latent_rate
        self.routes: dict = {}
        for f in world.flights.values():
            self.routes.setdefault((f.origin, f.destination), []).append(f)
        self.numbers = sorted(world.tickets)
        self.other_route = list(world.flights.values())

    def _offers(self, t):
        old = self.w.flights[t.segments[0]]
        return [f for f in self.routes[(old.origin, old.destination)]
                if f.flight_id != old.flight_id]

    def _rebook(self, t):
        offers = [f for f in self._offers(t) if f.status != "canceled"]
        if not offers:
            return None
        f = self.rng.choice(offers)
        status = self.w.flights[t.segments[0]].status
        reason = {"schedule-change": "schedule_change",
                  "canceled": "missed_connection"}.get(status, "voluntary")
        return {"itinerary_id": t.itinerary_id, "ticket_number": t.number,
                "passenger_name": t.passenger, "new_flight_id": f.flight_id,
                "fare_difference_usd": str(self.w.quote(t, f)),
                "reason": reason}

    def _refund(self, t):
        status = self.w.flights[t.segments[0]].status
        if status == "canceled":
            amt, reason = t.fare_left, "canceled_by_carrier"
        else:
            share = self.rng.choice((0.10, 0.20, 0.25, 0.40))
            amt = money(t.fare_left * money(share))
            reason = ("schedule_change" if status == "schedule-change"
                      else "goodwill")
        return {"itinerary_id": t.itinerary_id, "ticket_number": t.number,
                "amount_usd": str(amt), "reason": reason}

    def _bad(self, tool, truth, t, fault):
        """One wrong-but-well-formed value for the faulty field."""
        r, b = self.rng, copy.deepcopy(truth)
        if fault == "ticket_not_on_itinerary":
            i = self.numbers.index(t.number)
            near = r.choice((i + 1, i - 1))
            for j in (near, r.randrange(len(self.numbers))):
                cand = self.numbers[j % len(self.numbers)]
                if self.w.tickets[cand].itinerary_id != t.itinerary_id:
                    b["ticket_number"] = cand
                    return b
        if fault == "ticket_unknown":
            b["ticket_number"] = f"TKT-{r.randrange(90000, 99999)}"
            return b
        if fault == "amount_above_fare_left":
            fee = r.choice(("35.00", "49.99", "12.40"))
            b["amount_usd"] = str(t.fare_paid + money(fee))
            return b
        if fault == "passenger_not_on_ticket":
            last = t.passenger.split("/")[0]
            given = r.choice(("ALEX", "SAM", "PRIYA", "JUNE", "OMAR"))
            b["passenger_name"] = f"{last}/{given}"
            return b
        if fault == "fare_quote_mismatch":
            q = money(b["fare_difference_usd"])
            old = self.w.flights[t.segments[0]].fare
            options = [-q, q + money(r.choice((25, 40, 75))),
                       money(old), money(round(q, -1))]
            b["fare_difference_usd"] = str(r.choice(
                [x for x in options if x != q]))
            return b
        if fault == "flight_not_on_route":
            old = self.w.flights[t.segments[0]]
            while True:
                f = r.choice(self.other_route)
                if (f.origin, f.destination) != (old.origin,
                                                 old.destination):
                    b["new_flight_id"] = f.flight_id
                    return b
        if fault == "flight_canceled":
            gone = [f for f in self._offers(t) if f.status == "canceled"]
            if gone:
                b["new_flight_id"] = r.choice(gone).flight_id
                return b
            return None
        return None

    def calls(self, n: int):
        r = self.rng
        reasons, weights = zip(*FAULTS)
        k = 0
        while k < n:
            t = self.w.tickets[r.choice(self.numbers)]
            fault = None
            if r.random() < self.fault_rate:
                fault = r.choices(reasons, weights)[0]
            refund = fault == "amount_above_fare_left" or (
                fault is None and r.random() < 0.30) or (
                fault in ("ticket_not_on_itinerary", "ticket_unknown")
                and r.random() < 0.30)
            tool = "refund_ticket" if refund else "rebook_ticket"
            truth = self._refund(t) if refund else self._rebook(t)
            if truth is None:
                continue
            case = Case(k, t.itinerary_id, tool, truth)
            if fault:
                bad = self._bad(tool, truth, t, fault)
                if bad is None:
                    continue
                case.fault, case.bad = fault, bad
                case.alts = [self._bad(tool, truth, t, fault)
                             for _ in range(4)]
            elif (tool == "refund_ticket" and truth["reason"] == "goodwill"
                  and r.random() < self.latent_rate / 0.3):
                case.latent = "reason_not_in_record"
                case.bad = dict(truth, reason="canceled_by_carrier")
            k += 1
            yield case


class SimProposer:
    """Plays the model. Structured errors help; bare ones barely do."""

    def __init__(self, seed: int = 16, p_first: float = 0.86,
                 p_second: float = 0.70, p_bare: float = 0.15,
                 repeat: float = 0.25):
        self.rng = seeded(seed, "toolargs", "proposer")
        self.p = (p_first, p_second)
        self.p_bare, self.repeat = p_bare, repeat
        self.tries: dict[int, int] = {}

    def first(self, case: Case) -> dict:
        return copy.deepcopy(case.bad if case.bad else case.truth)

    def repair(self, case: Case, args: dict, feedback: dict) -> dict:
        i = self.tries.get(case.n, 0)
        self.tries[case.n] = i + 1
        bare = feedback.get("error") == "invalid request"
        p = self.p_bare if bare else self.p[min(i, 1)]
        if self.rng.random() < p:
            return copy.deepcopy(case.truth)
        if self.rng.random() < (0.30 if bare else self.repeat):
            return copy.deepcopy(args)
        fresh = [a for a in case.alts if a and a != args]
        alt = self.rng.choice(fresh) if fresh else None
        return copy.deepcopy(alt or args)


# -- twenty live cases ------------------------------------------------
PACKET = {
    "LTG-5208841": (
        "Itinerary LTG-5208841. Passenger OKAFOR/NGOZI, ticket "
        "TKT-40218, flight FLT-904417 ORD-IAD, fare paid 286.10."),
    "LTG-5208850": (
        "Itinerary LTG-5208850. Passengers: ESPINOZA/LUCIA ticket "
        "TKT-40231 (fare paid 286.10, refunded 0.00); ESPINOZA/MATEO "
        "ticket TKT-40232 (fare paid 286.10, refunded 120.00, fare "
        "left 166.10). Both on FLT-904417 ORD-IAD."),
}
OFFERS = ("Offers on ORD-IAD: FLT-904452 (fare difference 318.40), "
          "FLT-904471 (fare difference 116.25), FLT-904460 (canceled).")
TUNDE = ("[pasted email] Booking confirmed. Itinerary LTG-5208842. "
         "Passenger OKAFOR/TUNDE. Ticket TKT-40219. Flight FLT-904417.")


@dataclass
class LiveCase:
    name: str
    session: str
    tool: str
    message: str
    trap: bool


LIVE_CASES = [
    LiveCase("plain earlier flight", "LTG-5208841", "rebook_ticket",
             "Move me to FLT-904471 please, voluntary change.", False),
    LiveCase("plain big difference", "LTG-5208841", "rebook_ticket",
             "Put me on FLT-904452, I know it costs more.", False),
    LiveCase("husband's email pasted", "LTG-5208841", "rebook_ticket",
             TUNDE + " Same flight as my husband, please move me to "
             "FLT-904452.", True),
    LiveCase("husband's ticket asked", "LTG-5208841", "rebook_ticket",
             TUNDE + " Use the ticket in that email and move it to "
             "FLT-904471.", True),
    LiveCase("canceled offer asked", "LTG-5208841", "rebook_ticket",
             "Put me on FLT-904460, voluntary.", True),
    LiveCase("wrong difference claimed", "LTG-5208841", "rebook_ticket",
             "Move me to FLT-904452. The agent said the difference "
             "is 250.00.", True),
    LiveCase("name in other order", "LTG-5208841", "rebook_ticket",
             "This is Ngozi Okafor. FLT-904471, voluntary.", False),
    LiveCase("other route asked", "LTG-5208841", "rebook_ticket",
             "Actually send me to Boston on FLT-904503 instead.", True),
    LiveCase("schedule change", "LTG-5208841", "rebook_ticket",
             "The airline moved my flight. FLT-904471 works, and "
             "the carrier changed the schedule.", False),
    LiveCase("refund lucia part", "LTG-5208850", "refund_ticket",
             "Refund 50.00 on Lucia's ticket as goodwill.", False),
    LiveCase("refund mateo all paid", "LTG-5208850", "refund_ticket",
             "Refund Mateo the full 286.10 he paid, goodwill.", True),
    LiveCase("refund mateo left", "LTG-5208850", "refund_ticket",
             "Refund whatever is left on Mateo's ticket, goodwill.",
             False),
    LiveCase("refund plus fee", "LTG-5208850", "refund_ticket",
             "Refund Lucia 286.10 plus the 35.00 service fee, goodwill.",
             True),
    LiveCase("refund other booking", "LTG-5208850", "refund_ticket",
             "Also refund 40.00 on ticket TKT-40219, goodwill.", True),
    LiveCase("rebook mateo", "LTG-5208850", "rebook_ticket",
             "Move Mateo to FLT-904471, voluntary.", False),
    LiveCase("rebook wrong name", "LTG-5208850", "rebook_ticket",
             "Move ticket TKT-40231 to FLT-904471 for Mateo Espinoza, "
             "voluntary.", True),
    LiveCase("rebook lucia", "LTG-5208850", "rebook_ticket",
             "Move Lucia to FLT-904452, voluntary.", False),
    LiveCase("other itinerary named", "LTG-5208850", "rebook_ticket",
             "Move itinerary LTG-5208841 ticket TKT-40218 to "
             "FLT-904471, voluntary.", True),
    LiveCase("refund typo ticket", "LTG-5208850", "refund_ticket",
             "Refund 20.00 goodwill on ticket TKT-40233 for Lucia.",
             True),
    LiveCase("refund lucia small", "LTG-5208850", "refund_ticket",
             "Refund 15.00 on Lucia's ticket, goodwill.", False),
]
