"""Two verifiers for a rebooking outcome.

The pnr-reconciler (Chapter 6) reads the airline's booking record and
asks whether it matches what the agent proposed. It is right about
execution: the seat the agent asked for is the seat the airline holds.
It says nothing about whether the proposal was the right one.

The destination verifier asks a different question of a different
record: does the final destination the airline holds match the
destination the customer bought, as the booking system recorded it at
ticketing? A rebooking may change the flight, the time, even the
connection. Without the customer's own request in the session, it may
not change the city.
"""
from __future__ import annotations


def pnr_reconciler(proposal: dict, airline: dict) -> bool:
    """Airline record equals the proposal (flight and destination)."""
    return (airline["flight"] == proposal["flight"]
            and airline["destination"] == proposal["destination"])


def destination_verifier(ticketed: dict, airline: dict,
                         customer_asked: str | None = None) -> str:
    """'verified', 'wrong-destination', or 'desk' (a requested change
    of city, which a person confirms)."""
    if airline["destination"] == ticketed["destination"]:
        return "verified"
    if customer_asked == airline["destination"]:
        return "desk"
    return "wrong-destination"
