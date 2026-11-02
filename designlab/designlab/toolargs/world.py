"""World validation: do the identifiers in a call name real things that
belong together?

The store holds itineraries, the tickets on them, the passenger each
ticket is issued to, the flights on each ticket, and the refundable fare
left. It is built from the shared synthetic corpus plus three fixture
itineraries from the chapter's opening (LTG-5208841, LTG-5208842 and
LTG-5208850). Every rejection carries a reason code, the field it
concerns and a hint the model can act on. No hint names who an
identifier does belong to; an error message must not become a lookup
service.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import corpus
from common.rand import seeded
from corpus.names import FIRST

# Reason codes, in the order the checks run.
REASONS = (
    "itinerary_not_in_session",
    "ticket_unknown",
    "ticket_not_on_itinerary",
    "passenger_not_on_ticket",
    "flight_unknown",
    "flight_not_on_route",
    "flight_canceled",
    "fare_quote_mismatch",
    "amount_above_fare_left",
)

HINTS = {
    "itinerary_not_in_session":
        "this session acts on one itinerary; use the one in the packet",
    "ticket_unknown": "no such ticket; use a ticket from the packet",
    "ticket_not_on_itinerary":
        "ticket is not on this itinerary; use a ticket from the packet",
    "passenger_not_on_ticket":
        "name does not match the passenger on this ticket",
    "flight_unknown": "no such flight; use a flight from the offers",
    "flight_not_on_route":
        "new flight must fly the same origin and destination",
    "flight_canceled": "that flight is canceled; pick another offer",
    "fare_quote_mismatch":
        "fare difference must equal the quote for the new flight",
    "amount_above_fare_left":
        "amount exceeds the refundable fare left on this ticket",
}


@dataclass
class Ticket:
    number: str
    itinerary_id: str
    passenger: str            # SURNAME/GIVEN
    segments: list[str]
    fare_paid: Decimal
    refunded: Decimal = Decimal("0.00")

    @property
    def fare_left(self) -> Decimal:
        return self.fare_paid - self.refunded


@dataclass
class Flight:
    flight_id: str
    carrier: str
    origin: str
    destination: str
    status: str
    fare: Decimal


@dataclass
class Rejection:
    reason: str
    field: str
    hint: str

    def as_dict(self) -> dict:
        return {"reason": self.reason, "field": self.field,
                "hint": self.hint}


def norm_name(name: str) -> str:
    """'Ngozi Okafor', 'okafor/ngozi' and 'OKAFOR/NGOZI' are one name."""
    s = " ".join(name.replace(",", " ").split()).upper()
    if "/" in s:
        last, _, first = s.partition("/")
        return f"{last.strip()}/{first.strip()}"
    parts = s.split(" ")
    if len(parts) < 2:
        return s
    return f"{parts[-1]}/{' '.join(parts[:-1])}"


def money(s) -> Decimal:
    return Decimal(str(s)).quantize(Decimal("0.01"))


@dataclass
class World:
    tickets: dict[str, Ticket] = field(default_factory=dict)
    flights: dict[str, Flight] = field(default_factory=dict)
    itineraries: dict[str, list[str]] = field(default_factory=dict)
    lookups: int = 0

    # -- building -----------------------------------------------------
    def add_ticket(self, t: Ticket) -> None:
        self.tickets[t.number] = t
        self.itineraries.setdefault(t.itinerary_id, []).append(t.number)

    def offers(self, ticket: Ticket, n: int = 3) -> list[Flight]:
        """Flights on the same route as the ticket's first segment."""
        seg = self.flights[ticket.segments[0]]
        same = [f for f in self.flights.values()
                if f.origin == seg.origin
                and f.destination == seg.destination
                and f.flight_id != seg.flight_id
                and f.status != "canceled"]
        return same[:n]

    def quote(self, ticket: Ticket, new_flight: Flight) -> Decimal:
        old = self.flights[ticket.segments[0]]
        return money(new_flight.fare - old.fare)

    # -- checking -----------------------------------------------------
    def check(self, tool: str, args: dict, session_itinerary: str,
              rules: tuple = ()) -> Rejection | None:
        """Run the relationship checks in order; first failure wins."""
        def no(reason, fld):
            return Rejection(reason, fld, HINTS.get(reason, reason))

        if args["itinerary_id"] != session_itinerary:
            return no("itinerary_not_in_session", "itinerary_id")
        self.lookups += 1
        t = self.tickets.get(args["ticket_number"])
        if t is None:
            return no("ticket_unknown", "ticket_number")
        if t.itinerary_id != args["itinerary_id"]:
            return no("ticket_not_on_itinerary", "ticket_number")
        if tool == "rebook_ticket":
            if norm_name(args["passenger_name"]) != t.passenger:
                return no("passenger_not_on_ticket", "passenger_name")
            self.lookups += 1
            f = self.flights.get(args["new_flight_id"])
            if f is None:
                return no("flight_unknown", "new_flight_id")
            old = self.flights[t.segments[0]]
            if (f.origin, f.destination) != (old.origin, old.destination):
                return no("flight_not_on_route", "new_flight_id")
            if f.status == "canceled":
                return no("flight_canceled", "new_flight_id")
            if money(args["fare_difference_usd"]) != self.quote(t, f):
                return no("fare_quote_mismatch", "fare_difference_usd")
        elif tool == "refund_ticket":
            if money(args["amount_usd"]) > t.fare_left:
                return no("amount_above_fare_left", "amount_usd")
        for rule in rules:
            r = rule(self, tool, args, t)
            if r is not None:
                return r
        return None


# -- an optional cross-field rule (Try It Yourself) -------------------
def rule_reason_in_record(world, tool, args, ticket):
    """A refund labeled cancelled_by_carrier is billed back to the
    carrier, so the record must show the flight canceled. The reason and
    the ticket are each valid alone; together they can be false."""
    if tool != "refund_ticket" or \
            args["reason"] != "cancelled_by_carrier":
        return None
    if world.flights[ticket.segments[0]].status != "canceled":
        return Rejection("reason_not_in_record", "reason",
                         "the record shows no carrier cancellation")
    return None


RULES = {"reason-in-record": rule_reason_in_record}


# -- the store ----------------------------------------------------------
def _fixtures(w: World) -> None:
    """The chapter's opening: two bookings four minutes apart."""
    w.flights.update({
        "FLT-904417": Flight("FLT-904417", "XMY", "ORD", "IAD",
                             "scheduled", money("286.10")),
        "FLT-904452": Flight("FLT-904452", "XMY", "ORD", "IAD",
                             "scheduled", money("604.50")),
        "FLT-904460": Flight("FLT-904460", "XMY", "ORD", "IAD",
                             "canceled", money("341.00")),
        "FLT-904471": Flight("FLT-904471", "XMY", "ORD", "IAD",
                             "scheduled", money("402.35")),
        "FLT-904503": Flight("FLT-904503", "XMY", "ORD", "BOS",
                             "scheduled", money("251.00")),
    })
    w.add_ticket(Ticket("TKT-40218", "LTG-5208841", "OKAFOR/NGOZI",
                        ["FLT-904417"], money("286.10")))
    w.add_ticket(Ticket("TKT-40219", "LTG-5208842", "OKAFOR/TUNDE",
                        ["FLT-904417"], money("286.10")))
    # a two-passenger booking for the live cases
    w.add_ticket(Ticket("TKT-40231", "LTG-5208850", "ESPINOZA/LUCIA",
                        ["FLT-904417"], money("286.10")))
    w.add_ticket(Ticket("TKT-40232", "LTG-5208850", "ESPINOZA/MATEO",
                        ["FLT-904417"], money("286.10"),
                        refunded=money("120.00")))


def build(seed: int = 2026, itineraries: int = 3000,
          companion_share: float = 0.25) -> World:
    c = corpus.generate(seed=seed)
    w = World()
    for f in c["flights"]:
        w.flights[f["flight_id"]] = Flight(
            f["flight_id"], f["carrier"], f["origin"], f["destination"],
            f["status"], money(f["fare_usd"]))
    names = {cu["customer_id"]: cu["name"] for cu in c["customers"]}
    rng = seeded(seed, "toolargs", "world")
    n = 10000
    for it in c["itineraries"][:itineraries]:
        lead = names[it["customer_id"]]
        given, surname = lead.split(" ", 1)
        people = [f"{surname.upper()}/{given.upper()}"]
        if rng.random() < companion_share:
            other = rng.choice([g for g in FIRST if g != given])
            people.append(f"{surname.upper()}/{other.upper()}")
        fare = money(sum(w.flights[s].fare for s in it["segments"]))
        for p in people:
            n += 1
            w.add_ticket(Ticket(f"TKT-{n:05d}", it["itinerary_id"], p,
                                list(it["segments"]), fare))
    _fixtures(w)
    return w
