"""Lakeshore's document corpus for retrieval (Chapter 19).

Four kinds of document, as the knowledge plane indexes them:
  fare-rule   one carrier's rule on one topic, versioned by effective
              date (fares.lakeshore.internal)
  notice      a carrier's waiver or schedule notice
              (notices.lakeshore.internal)
  supplier    a hotel or car supplier's change policy
              (docs.lakeshore.internal)
  help        Lakeshore help-center articles, carrier-agnostic, written
              in customers' words (docs.lakeshore.internal)
  note        agent-desk case notes, which quote whatever applied that
              day and are never a source for a rule

Versions are the point. A rule page has an effective_from date and, once
replaced, an effective_to date and the id of the version that replaced
it. Every version stays in the index, because a ticket issued in April
is still priced by April's rule. Seeded; the same seed gives the same
documents. Adds a module; does not change corpus.generate output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache

from common.rand import DEFAULT_SEED, seeded

INDEXED_AT = "2026-05-04T14:14:02-05:00"   # the re-crawl before the call

CARRIERS = (
    ("XPA", "Prairie Airways"), ("XHA", "Harbor Air"),
    ("XSU", "Summit Airlines"), ("XNL", "Northline Jet"),
    ("XBW", "Bluewing Express"), ("XCA", "Cardinal Airways"),
    ("XME", "Meridian Air"), ("XTW", "Tidewater Airlines"),
    ("XGR", "Granite Airways"), ("XSL", "Silverleaf Air"),
    ("XWE", "Westerly Airlines"), ("XCO", "Copperline Jet"),
    ("XEV", "Evergreen Wings"), ("XJU", "Juniper Air"),
    ("XRB", "Riverbend Airways"), ("XSK", "Skyhollow Airlines"),
    ("XFR", "Falconridge Air"), ("XSB", "Seabright Airways"),
    ("XHM", "Highmark Express"), ("XLW", "Lakeway Airlines"),
)
PRODUCTS = ("Basic", "Main", "Flex")

# topic: (title, rule words, customer words)
TOPICS = {
    "same-day": (
        "same-day change",
        "same-day change to an earlier or later flight on the day of "
        "departure, subject to seat availability",
        ("switch to an earlier flight on the day I travel",
         "take a later flight the same day",
         "hop on an earlier departure on my travel day",
         "move to another flight on the day of travel")),
    "change-fee": (
        "voluntary change fee",
        "voluntary change to a different date or flight before "
        "departure; fare difference applies",
        ("move my trip to another date",
         "change my booking to next week",
         "pay to rebook for a different day",
         "push my flight back a few days")),
    "cancel": (
        "cancellation and refund",
        "voluntary cancellation before departure and the refund or "
        "travel credit due",
        ("cancel my ticket and get money back",
         "call off the trip and get a refund",
         "what happens to my money if I cancel",
         "cancel and keep the value as credit")),
    "schedule": (
        "involuntary schedule change",
        "carrier-initiated schedule change; rebooking or refund when "
        "the departure moves by more than the threshold",
        ("the airline moved my flight time",
         "my departure was retimed by the carrier",
         "they shifted my flight by hours",
         "the carrier changed my schedule")),
    "name": (
        "name correction",
        "correction of a misspelled passenger name on an issued ticket",
        ("fix a typo in the passenger name",
         "my name is spelled wrong on the ticket",
         "correct the spelling of a traveler's name",
         "the ticket has a misspelled surname")),
    "no-show": (
        "no-show",
        "failure to board a booked segment; later segments are "
        "canceled unless the carrier is told before departure",
        ("I missed my flight",
         "skip the first leg of my trip",
         "did not make it to the gate",
         "what if I do not turn up for the outbound")),
    "baggage": (
        "checked baggage",
        "checked baggage allowance and fees per bag",
        ("check a suitcase",
         "bring a second bag",
         "how much for luggage in the hold",
         "pay for a checked bag")),
    "upgrade": (
        "upgrade",
        "paid upgrade to a higher cabin before or at check-in",
        ("move up to a better seat",
         "buy a seat in the front cabin",
         "get a nicer cabin on the day",
         "pay to sit in premium")),
}

# Values each topic can take, by product. Strings, as a page states them.
VALUES = {
    "same-day": ((None, "75", "0"), (None, "100", "0"), ("75", "50", "0")),
    "change-fee": ((None, "0", "0"), (None, "99", "0"), ("150", "0", "0")),
    "cancel": (("no refund", "travel credit", "refund"),
               ("no refund", "credit less $99", "refund")),
    "schedule": (("90", "90", "60"), ("120", "120", "60"),
                 ("180", "120", "60")),
    "name": (("2", "3", "3"), ("1", "3", "4")),
    "no-show": (("forfeit", "forfeit", "credit"),
                ("forfeit", "credit less $99", "credit")),
    "baggage": (("45", "35", "0"), ("40", "35", "0"), ("50", "40", "0")),
    "upgrade": ((None, "from $89", "from $59"), (None, "from $129",
                                                 "from $79")),
}
CHANGE_DATES = (date(2026, 2, 1), date(2026, 3, 15), date(2026, 4, 1),
                date(2026, 5, 1))
FUTURE_DATE = date(2026, 6, 1)
FIRST_DATE = date(2025, 1, 1)


@dataclass(frozen=True)
class Doc:
    doc_id: str
    kind: str
    title: str
    text: str
    source: str
    effective_from: date
    effective_to: date | None = None
    superseded_by: str | None = None
    carrier: str | None = None
    topic: str | None = None
    version: int = 1
    facts: dict = field(default_factory=dict, compare=False, hash=False)

    def in_effect(self, as_of: date) -> bool:
        if as_of < self.effective_from:
            return False
        return self.effective_to is None or as_of <= self.effective_to


def _value_line(topic: str, product: str, v: str | None) -> str:
    if v is None:
        return f"{product}: not permitted."
    if topic in ("same-day", "change-fee"):
        return (f"{product}: no fee." if v == "0"
                else f"{product}: ${v} per passenger.")
    if topic == "schedule":
        return (f"{product}: free rebooking or refund if departure moves "
                f"by more than {v} minutes.")
    if topic == "name":
        return f"{product}: up to {v} characters corrected at no charge."
    if topic == "baggage":
        return (f"{product}: no fee for the first bag." if v == "0"
                else f"{product}: ${v} for the first bag.")
    return f"{product}: {v}."


def _rule_text(code: str, name: str, topic: str, values, ref: str,
               start: date, long: bool, replaces: str | None) -> str:
    title, words, _ = TOPICS[topic]
    issued = start.strftime('%B %-d, %Y')
    if replaces:
        # Revisions are published as short notices of what changed.
        lines = [f"{name} ({code}) fare rules: {title}, revised.",
                 f"For tickets issued from {issued}:"]
    else:
        lines = [f"{name} ({code}) fare rules: {title}.",
                 f"Applies to tickets issued on or after {issued}.",
                 f"Covers a {words}."]
    lines += [_value_line(topic, p, v) for p, v in zip(PRODUCTS, values)]
    lines.append(f"Rule reference {ref}."
                 + (f" Replaces {replaces}." if replaces else ""))
    if long:
        lines.append(f"The {title} rule applies per passenger and per "
                     f"direction; {name} may refuse a {title} when the "
                     f"booking class is closed. Agents should quote the "
                     f"{title} amount from this page and record the "
                     f"rule reference.")
    return " ".join(lines)


def _rules(seed: int) -> list[Doc]:
    rng = seeded(seed, "docs", "rules")
    refs = seeded(seed, "docs", "refs")
    out: list[Doc] = []
    for code, name in CARRIERS:
        for topic in TOPICS:
            opts = VALUES[topic]
            plan = [(FIRST_DATE, rng.choice(opts))]
            roll = rng.random()
            if roll < 0.30:
                plan.append((rng.choice(CHANGE_DATES), rng.choice(opts)))
            elif roll < 0.38:
                plan.append((FUTURE_DATE, rng.choice(opts)))
            if (code, topic) == ("XPA", "same-day"):
                # The opening of Chapter 19: version 1 to April 30,
                # version 2 from May 1, 2026.
                plan = [(FIRST_DATE, (None, "75", "0")),
                        (date(2026, 5, 1), (None, "100", "0"))]
            vers = []
            prev = None
            for i, (start, vals) in enumerate(plan, 1):
                end = None
                if i < len(plan):
                    end = date.fromordinal(plan[i][0].toordinal() - 1)
                # The first version was written long; revisions short.
                long = i == 1
                vid = f"FR-{code}-{topic}-v{i}"
                ref = f"{code}-{refs.randint(1000, 9999)}"
                vers.append(Doc(
                    doc_id=vid, kind="fare-rule",
                    title=f"{name} ({code}) fare rules: "
                          f"{TOPICS[topic][0]}",
                    text=_rule_text(code, name, topic, vals, ref, start,
                                    long, prev),
                    source=f"fares.lakeshore.internal/rules/{code}/"
                           f"{topic}/v{i}",
                    effective_from=start, effective_to=end,
                    superseded_by=(f"FR-{code}-{topic}-v{i + 1}"
                                   if end else None),
                    carrier=code, topic=topic, version=i,
                    facts=dict(zip(PRODUCTS, vals), ref=ref)))
                prev = ref
            out += vers
    return out


NOTICE_EVENTS = (
    ("DEN", "winter storm", date(2026, 2, 1), date(2026, 2, 3)),
    ("ORD", "thunderstorms", date(2026, 5, 12), date(2026, 5, 14)),
    ("BOS", "nor'easter", date(2026, 3, 9), date(2026, 3, 10)),
    ("MIA", "tropical storm", date(2026, 6, 4), date(2026, 6, 6)),
)


def _notices(seed: int) -> list[Doc]:
    rng = seeded(seed, "docs", "notices")
    out = []
    for i, (code, name) in enumerate(CARRIERS):
        for j, (apt, event, d0, d1) in enumerate(NOTICE_EVENTS):
            if (i + j) % 2:
                continue
            basic = rng.random() < 0.5
            by = date.fromordinal(d1.toordinal() + 7)
            text = (f"{name} ({code}) travel waiver: {event} at {apt}. "
                    f"Customers ticketed to travel through {apt} from "
                    f"{d0.strftime('%B %-d')} to "
                    f"{d1.strftime('%B %-d, %Y')} may change once "
                    f"without a change fee to travel by "
                    f"{by.strftime('%B %-d, %Y')}. Fare difference may "
                    f"apply. Basic fares are "
                    f"{'included' if basic else 'excluded'}. Waiver code "
                    f"{code}-WV-{apt}.")
            nid = f"NT-{code}-{apt}"
            out.append(Doc(
                doc_id=nid, kind="notice",
                title=f"{name} waiver: {event} at {apt}", text=text,
                source=f"notices.lakeshore.internal/{code}/{apt}",
                effective_from=date.fromordinal(d0.toordinal() - 3),
                carrier=code, topic=f"waiver-{apt}",
                facts={"Basic": "included" if basic else "excluded",
                       "travel_by": by.isoformat()}))
    return out


SUPPLIERS = (
    ("Maple Suites", "hotel"), ("Harborview Hotels", "hotel"),
    ("Linden Inns", "hotel"), ("Stonegate Resorts", "hotel"),
    ("Willow Lodges", "hotel"), ("Crescent Hotels", "hotel"),
    ("Bayfront Stays", "hotel"), ("Oakhurst Hotels", "hotel"),
    ("Larkspur Car Rental", "car"), ("Ashford Car Hire", "car"),
    ("Brightwater Cars", "car"), ("Cedar Auto Rental", "car"),
)


def _suppliers(seed: int) -> list[Doc]:
    rng = seeded(seed, "docs", "suppliers")
    out = []
    for name, kind in SUPPLIERS:
        hours = rng.choice((24, 48, 72))
        fee = rng.choice((0, 25, 50))
        slug = name.split()[0].lower()
        if kind == "hotel":
            text = (f"{name} cancellation policy. Reservations may be "
                    f"canceled without penalty up to {hours} hours before "
                    f"check-in. Later cancellations are charged one "
                    f"night. Date changes are free when made {hours} "
                    f"hours ahead; prepaid rates are nonrefundable.")
        else:
            text = (f"{name} change policy. Pickup time or location may "
                    f"be changed up to {hours} hours before pickup"
                    f"{'' if fee == 0 else f' for ${fee}'}. No-shows "
                    f"forfeit prepaid amounts.")
        out.append(Doc(
            doc_id=f"SP-{slug}", kind="supplier",
            title=f"{name} change and cancellation policy", text=text,
            source=f"docs.lakeshore.internal/suppliers/{slug}",
            effective_from=FIRST_DATE, topic=kind,
            facts={"hours": hours, "fee": fee}))
    return out


def _help() -> list[Doc]:
    out = []
    for topic, (title, words, says) in TOPICS.items():
        for k, say in enumerate(says[:3]):
            text = (f"Help center: {say}? Most airlines call this a "
                    f"{title}. It covers a {words}. The amount depends on "
                    f"the airline and the fare you bought, Basic, Main or "
                    f"Flex, and on the date your ticket was issued. Ask "
                    f"us to {say.lower()} and we will check your "
                    f"airline's current rule before quoting a fee.")
            out.append(Doc(
                doc_id=f"HC-{topic}-{k + 1}", kind="help",
                title=f"Help: {say}", text=text,
                source=f"docs.lakeshore.internal/help/{topic}/{k + 1}",
                effective_from=FIRST_DATE, topic=topic))
    return out


OUTCOMES = ("customer accepted", "customer declined", "sent to supervisor",
            "customer will call back", "waiver requested from carrier")


def _notes(seed: int, n: int = 300) -> list[Doc]:
    """Agent-desk case notes. They talk like customers, quote whatever
    amount applied that day, and are never a source for a fare rule."""
    rng = seeded(seed, "docs", "notes")
    out = []
    topics = list(TOPICS)
    for k in range(n):
        code, name = rng.choice(CARRIERS)
        topic = rng.choice(topics)
        title, _, says = TOPICS[topic]
        day = date.fromordinal(date(2025, 6, 1).toordinal()
                               + rng.randint(0, 330))
        prod = rng.choice(PRODUCTS)
        amt = rng.choice(("$50", "$75", "$99", "$100", "$150", "no fee"))
        text = (f"Case note {day.isoformat()}: customer on {name} with a "
                f"{prod} fare asked to {rng.choice(says).lower()}. "
                f"Quoted {amt} for the {title}. "
                f"{rng.choice(OUTCOMES).capitalize()}.")
        out.append(Doc(
            doc_id=f"CN-{k + 1:04d}", kind="note",
            title=f"Case note {day.isoformat()}", text=text,
            source=f"docs.lakeshore.internal/desk-notes/{k + 1:04d}",
            effective_from=day, carrier=code, topic=topic))
    return out


@lru_cache(maxsize=4)
def documents(seed: int = DEFAULT_SEED) -> tuple[Doc, ...]:
    return tuple(_rules(seed) + _notices(seed) + _suppliers(seed)
                 + _help() + _notes(seed))


def by_id(seed: int = DEFAULT_SEED) -> dict[str, Doc]:
    return {d.doc_id: d for d in documents(seed)}


def in_effect(carrier: str, topic: str, as_of: date,
              seed: int = DEFAULT_SEED) -> Doc | None:
    for d in documents(seed):
        if (d.kind in ("fare-rule", "notice") and d.carrier == carrier
                and d.topic == topic and d.in_effect(as_of)):
            return d
    return None


def carrier_name(code: str) -> str:
    return dict(CARRIERS)[code]
