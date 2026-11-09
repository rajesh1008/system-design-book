"""The two effect tools whose arguments the chapter checks.

Each tool has a name, a version and an input schema. The version moves
when the effect changes, not when the wording does (Chapter 16): rebook
2.1 added `ticket_number` on April 20, 2026, for carriers that reissue
by ticket, and the gateway kept accepting 2.0 calls for one release.
"""
from __future__ import annotations

MONEY = r"^-?[0-9]{1,5}\.[0-9]{2}$"

REBOOK_V2_1 = {
    "name": "rebook_ticket",
    "version": "2.1",
    "description": (
        "Reissue one passenger's ticket on a new flight. Use only "
        "identifiers that appear in the case's context packet. "
        "fare_difference_usd is new fare minus old, as a decimal "
        "string with two places."),
    "input_schema": {
        "type": "object",
        "properties": {
            "itinerary_id": {"type": "string",
                             "pattern": r"^LTG-[0-9]{7}$"},
            "ticket_number": {"type": "string",
                              "pattern": r"^TKT-[0-9]{5}$"},
            "passenger_name": {"type": "string"},
            "new_flight_id": {"type": "string",
                              "pattern": r"^FLT-[0-9]{6}$"},
            "fare_difference_usd": {"type": "string",
                                    "pattern": MONEY},
            "reason": {"type": "string",
                       "enum": ["voluntary", "schedule_change",
                                "missed_connection"]},
        },
        "required": ["itinerary_id", "ticket_number",
                     "passenger_name", "new_flight_id",
                     "fare_difference_usd", "reason"],
        "additionalProperties": False,
    },
}

REFUND_V3 = {
    "name": "refund_ticket",
    "version": "3.0",
    "description": (
        "Ask the processor to refund part or all of one ticket. "
        "amount_usd is a decimal string with two places and may not "
        "exceed the refundable fare left on the ticket."),
    "input_schema": {
        "type": "object",
        "properties": {
            "itinerary_id": {"type": "string",
                             "pattern": r"^LTG-[0-9]{7}$"},
            "ticket_number": {"type": "string",
                              "pattern": r"^TKT-[0-9]{5}$"},
            "amount_usd": {"type": "string",
                           "pattern": r"^[0-9]{1,5}\.[0-9]{2}$"},
            "reason": {"type": "string",
                       "enum": ["canceled_by_carrier", "schedule_change",
                                "goodwill"]},
        },
        "required": ["itinerary_id", "ticket_number", "amount_usd",
                     "reason"],
        "additionalProperties": False,
    },
}

TOOLS = {t["name"]: t for t in (REBOOK_V2_1, REFUND_V3)}


def api_tool(tool: dict, strict: bool = True) -> dict:
    """The definition as the Messages API takes it.

    The API's constrained decoding does not enforce numeric bounds or
    string lengths, so nothing here relies on them; the gateway's own
    validator runs the full schema either way.
    """
    out = {"name": tool["name"], "description": tool["description"],
           "input_schema": tool["input_schema"]}
    if strict:
        out["strict"] = True
    return out
