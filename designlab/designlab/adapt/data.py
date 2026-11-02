"""Six months of change requests, December 2025 to May 2026.

Each case is one customer asking for one change; about a third of cases
send more than one message (a resend or a follow-up that repeats the
booking reference). A small share of messages are vague: the text alone
does not say which change is wanted, and only the system of record does.
Lakeshore Flex, launched in April 2026, adds new words, and from April
the app's chat window sends a growing share of messages in shorthand
("cxl my flt, rfnd pls"), which the training months never saw. Times
carry Chicago offsets (CST, -06:00, until March 8, 2026; CDT after).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from common.rand import seeded

CHICAGO = ZoneInfo("America/Chicago")
MONTHS = ("2025-12", "2026-01", "2026-02", "2026-03", "2026-04",
          "2026-05")

# Annual volumes from Chapter 4, in thousands; they weight the mix.
TYPES = {
    "voluntary_rebook": 330, "cancel_credit": 300,
    "involuntary_rebook": 260, "hotel_cancel": 220,
    "cancel_refund": 210, "involuntary_refund": 190, "upgrade": 150,
    "accept_schedule": 130, "hotel_date_change": 120,
    "ancillary_refund": 80, "car_change": 60, "name_correction": 50,
}

PHRASES = {
    "voluntary_rebook": [
        "i want to move my flight to a later day",
        "can i change my flight to the morning one",
        "i need to fly out a day earlier, please change it",
        "please switch me to the evening flight",
        "my plans changed and i need a different date",
        "i would like to rebook onto the friday flight",
    ],
    "cancel_credit": [
        "please cancel my trip and keep the value as credit",
        "cancel the flight, i will use the credit later",
        "i cannot go, put the money toward a future trip",
        "cancel it and give me a travel credit",
        "i want to cancel and save the fare for next time",
    ],
    "involuntary_rebook": [
        "the airline canceled my flight, i need another one",
        "my flight was moved by hours and i cannot make it, find me another",
        "you changed my departure and i missed the connection, rebook me",
        "the carrier dropped my route, put me on the next flight",
        "my connection no longer works after the schedule change, "
        "get me a new itinerary",
    ],
    "hotel_cancel": [
        "please cancel my hotel reservation",
        "i no longer need the room, cancel the hotel",
        "cancel the hotel part of my booking",
        "drop the hotel, keep the flights",
    ],
    "cancel_refund": [
        "cancel my trip and refund the card",
        "i want to cancel and get my money back",
        "please cancel and send the refund to my original payment",
        "cancel the flight, i need a refund not credit",
        "cancel everything and refund me",
    ],
    "involuntary_refund": [
        "the airline canceled my flight and i want a refund",
        "my flight was canceled, i do not want another, refund me",
        "since you changed the schedule i want my money back",
        "the carrier canceled, please refund instead of rebooking",
    ],
    "upgrade": [
        "can i upgrade to business on my flight",
        "how much to move up to first class",
        "i would like to buy an upgrade for the long leg",
        "please upgrade my seat to premium economy",
    ],
    "accept_schedule": [
        "the new departure time is fine, i accept it",
        "i got the schedule change notice and the new time works",
        "ok with the new flight time, please confirm",
        "i accept the changed itinerary",
    ],
    "hotel_date_change": [
        "please move my hotel stay by one night",
        "i need the hotel from tuesday instead of monday",
        "can you change my hotel dates to match the new flight",
        "extend my hotel by a night",
    ],
    "ancillary_refund": [
        "i paid for a seat i never got, refund the seat fee",
        "my bag fee was charged twice, please refund one",
        "refund the wifi purchase, it never worked",
        "i was charged for priority boarding but did not get it",
    ],
    "car_change": [
        "change my rental car pickup to the next day",
        "i need a bigger car on my rental",
        "move the car pickup to the airport location",
        "cancel the rental car upgrade but keep the car",
    ],
    "name_correction": [
        "my last name is misspelled on the ticket",
        "please fix the spelling of my first name",
        "the name on the booking does not match my passport",
        "correct my middle name on the reservation",
    ],
}

# Lakeshore Flex, a fare product launched in April 2026, brings words the
# training months never used, and the same word in several types.
FLEX_FROM = "2026-04"
FLEX_SHARE = {"2026-04": 0.10, "2026-05": 0.22}
LATE = {
    "cancel_credit": ["put the whole fare into flex",
                      "flex it, i will travel later",
                      "send the fare to my flex wallet"],
    "voluntary_rebook": ["use my flex change for the 6 pm departure",
                         "flex me onto the earlier one"],
    "cancel_refund": ["i bought flex refund, so cancel and pay me back",
                      "cash out my flex fare to the card"],
    "ancillary_refund": ["the flex fee was charged but i never chose flex",
                         "take the flex add-on off and give that back"],
    "upgrade": ["can my flex fare move up a cabin"],
}

VAGUE = [
    "i need help with my booking for next week",
    "something is wrong with my trip, please fix it",
    "can someone look at my reservation",
    "please sort out my booking",
]

OPENERS = ["", "hi, ", "hello, ", "good morning, ", "hey, ", "quick one, "]
CLOSERS = ["", " thanks", " thank you", " asap please", " thx",
           " appreciate it"]
CITIES = ["chicago", "denver", "boston", "austin", "seattle", "miami",
          "phoenix", "atlanta", "dallas", "newark", "orlando", "portland"]
SHORT = {"cancel": "cxl", "canceled": "cxld", "flight": "flt",
         "refund": "rfnd", "please": "pls", "hotel": "htl",
         "reservation": "res", "change": "chg", "changed": "chgd",
         "upgrade": "upg", "credit": "cr", "booking": "bkg",
         "schedule": "sched", "rental": "rntl", "money": "$",
         "tomorrow": "tmrw", "airline": "carrier", "want": "wnt",
         "need": "nd", "my": "my", "the": "", "and": "+",
         "name": "nm", "seat": "st", "date": "dt", "night": "nt"}
SHORTHAND = {"2026-04": 0.12, "2026-05": 0.18}
UNCLEAR = "unclear"

FOLLOW = ["following up on my request", "sending this again",
          "any update on this", "still waiting on this"]


@dataclass(frozen=True)
class Message:
    msg_id: str
    case_id: str
    month: str
    at: str                 # ISO time with the Chicago offset
    text: str
    label: str              # the right answer for the step
    vague: bool             # the text does not say; answer "unclear"
    wanted: str             # what the system of record shows later
    short: bool = False


def _when(rng, month: str) -> str:
    y, m = (int(p) for p in month.split("-"))
    day = rng.randint(1, 28)
    t = datetime(y, m, day, rng.randint(6, 21), rng.randint(0, 59),
                 tzinfo=CHICAGO)
    return t.isoformat()


def _phrase(rng, label: str, month: str) -> str:
    if label in LATE and rng.random() < FLEX_SHARE.get(month, 0.0):
        return rng.choice(LATE[label])
    return rng.choice(PHRASES[label])


def shorthand(text: str) -> str:
    words = [SHORT.get(w, w) for w in text.split(" ")]
    return " ".join(w for w in words if w)


def generate(seed: int = 17, per_month: int = 600,
             golden_month: str = "2026-05", golden_per_type: int = 100,
             vague_rate: float = 0.04, extra_types: dict | None = None
             ) -> list[Message]:
    """Messages for every month. The golden month has 100 cases a type."""
    phrases = dict(PHRASES)
    types = dict(TYPES)
    for name, (start, pool, weight) in (extra_types or {}).items():
        phrases[name] = pool
        types[name] = weight
    out: list[Message] = []
    n = 0
    for month in MONTHS:
        rng = seeded(seed, "adapt", "data", month)
        if month == golden_month:
            labels = [t for t in types for _ in range(golden_per_type)
                      if _active(t, month, extra_types)]
        else:
            act = [t for t in types if _active(t, month, extra_types)]
            labels = rng.choices(act, weights=[types[t] for t in act],
                                 k=per_month)
        rng.shuffle(labels)
        for label in labels:
            n += 1
            case = f"C{n:06d}"
            ref = f"ltg{rng.randint(1000000, 9999999)}"
            vague = rng.random() < vague_rate
            if label in PHRASES:
                body = rng.choice(VAGUE) if vague else \
                    _phrase(rng, label, month)
            else:
                body = rng.choice(phrases[label])
                vague = False
            city = rng.choice(CITIES)
            short = rng.random() < SHORTHAND.get(month, 0.0)
            if short:
                body = shorthand(body)
            texts = [f"{rng.choice(OPENERS)}{body}, booking {ref} "
                     f"to {city}.{rng.choice(CLOSERS)}"]
            if short:
                texts = [shorthand(texts[0])]
            k = rng.random()
            if k < 0.22:
                texts.append(texts[0])                 # a resend
            elif k < 0.34:
                texts.append(f"{rng.choice(FOLLOW)}, booking {ref}: "
                             f"{body}")
            for i, text in enumerate(texts):
                out.append(Message(f"{case}-{i + 1}", case, month,
                                   _when(rng, month), text,
                                   UNCLEAR if vague else label, vague,
                                   label, short))
    return out


def _active(label: str, month: str, extra: dict | None) -> bool:
    if extra and label in extra:
        return month >= extra[label][0]
    return True


def by_month(msgs: list[Message]) -> dict[str, list[Message]]:
    out: dict[str, list[Message]] = {m: [] for m in MONTHS}
    for m in msgs:
        out[m.month].append(m)
    return out
