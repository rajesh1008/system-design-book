"""Chapter 22 lab: the governed memory store.

Parts (all by default):
    pilot      the pilot's note store against the governed store, on
               one customer's single aisle request
    write      the write gate; with --no-provenance, the injected
               failure: a memory written without a source event
    supersede  compare-and-set on the head, and the version floor
    scope      tenant from the token, read policy by role, sessions
    authority  a remembered promise as grounds for a voucher
    forget     erasure through derived_from, and a restore
    audit      the pilot's legacy notes, sorted
    pack       memories into the context assembler's memory slot

Offline; seed 22; no model call and no key. US dollars. Times are
America/Chicago.
"""
from __future__ import annotations

import argparse
import json
import sys

from chain.record import Proposal
from common.clock import FixedClock
from common.rand import seeded
from common.trail import TrailWriter, check_trail
from isolation.blast import OutOfScope
from planes import ControlPlane, ContextPacket, Fact, TrailPlane, World
from planes.autonomy import load_autonomy

from .audit import audit_legacy
from .forget import forget, naive_forget, remaining, restore, snapshot
from .policy import authorize
from .record import Draft, Source
from .render import to_items
from .store import (MemoryStore, OlderThanHead, SessionToken, StaleHead,
                    WriteRefused)

LUCIA = "CUS-018342"
TOKYO = "LTG-5520317"           # February 2026, Chicago to Tokyo
LATER = ("LTG-5561048", "LTG-5583321", "LTG-5590274")
COMPANION = "CUS-018343"
START = "2026-05-04T09:00:00-05:00"
TURN = Source("CON-7730115", "customer-stated",
              "Could I get an aisle on the Tokyo flight? My knee.")


def say(s: str = "") -> None:
    assert len(s) <= 70, s
    print(s)


def new_store(step: float = 1.0) -> MemoryStore:
    clock = FixedClock(START, step_seconds=step)
    return MemoryStore(clock, TrailWriter(clock=clock),
                       trip_ends={TOKYO: "2026-02-20T23:59:00-06:00"})


def tok(it: str, n: int = 1, role: str = "agent-loop",
        tenant: str = LUCIA) -> SessionToken:
    return SessionToken(f"SES-{it[-4:]}-{n}", tenant, it, role)


# ------------------------------------------------------------- pilot
def part_pilot() -> None:
    say("pilot note store (as configured, November 2025):")
    notes = [{"customer": LUCIA, "note": "prefers an aisle seat"}]
    for it in LATER:
        got = [n["note"] for n in notes if n["customer"] == LUCIA]
        seat = "aisle" if any("aisle" in g for g in got) else "none"
        say(f"  {it}  seat preference read: {seat}")
    say("  source: none  scope: none  confidence: none")
    say()
    say("governed store, same turn:")
    s = new_store()
    # The Tokyo session ran in February; the lab writes it with the
    # observation time from the turn.
    rec = s.write(tok(TOKYO), Draft("seat", "aisle", "trip", TURN, 0.9,
                                    trip=TOKYO,
                                    observed_at="2026-02-09T18:40:00-06:00"))
    say(f"  {rec.memory_id} seat=aisle scope=trip {rec.trip}")
    say(f"  source {rec.source.event_id} {rec.source.kind}")
    for it in LATER:
        got = s.read(tok(it))
        seat = got[0].value if got else "none"
        say(f"  {it}  seat preference read: {seat}")


# ------------------------------------------------------------- write
def part_write(no_provenance: bool = False) -> int:
    s = new_store()
    t = tok(LATER[2])
    cases = [("one trip, customer-stated",
              Draft("seat", "aisle", "trip", TURN, 0.9, trip=LATER[2])),
             ("standing, customer-stated",
              Draft("seat", "aisle", "standing", TURN, 0.9)),
             ("refund, agent-inferred",
              Draft("refund", "original card", "standing",
                    Source("CON-7730120", "agent-inferred"), 0.8))]
    if no_provenance:
        cases = [("no source, no scope (pilot shape)",
                  Draft("seat", "aisle", None, None, None))]
    refused = 0
    for label, d in cases:
        try:
            r = s.write(t, d)
            say(f"{label}: written {r.memory_id}")
        except WriteRefused as e:
            refused += 1
            say(f"{label}:")
            for m in e.missing:
                say(f"  refused: {m}")
    say(f"writes refused: {refused} of {len(cases)}")
    last = json.loads(s.trail.lines[-1])
    say(f"trail line {len(s.trail.lines)}: {last['kind']} at "
        f"{last['at'][11:19]}")
    say(f"trail intact: {not check_trail(s.trail.lines)}")
    return refused


# --------------------------------------------------------- supersede
def part_supersede() -> None:
    s = new_store()
    t = tok(LATER[2])
    confirmed = Source("CON-7731402", "customer-confirmed",
                       "Window from now on, please.")
    v1 = s.write(t, Draft("seat", "window", "standing", confirmed, 0.95,
                          observed_at="2026-05-04T10:12:00-05:00"))
    say(f"v1 {v1.memory_id} window, head None to {v1.memory_id}")
    # The migration job read the head before v1 existed.
    legacy = Draft("seat", "aisle", "standing",
                   Source("CON-7730115", "desk-entered"), 0.6,
                   observed_at="2026-02-09T18:40:00-06:00")
    try:
        s.write(t, legacy, expected_head=None)
    except StaleHead as e:
        say(f"migration write: stale head, expected {e.expected}, "
            f"head {e.head}")
    try:
        s.write(t, legacy, expected_head=s.head(t, "seat", "standing"))
    except OlderThanHead as e:
        say(f"retry on the new head: refused, {e.missing[0]}")
    later = Source("CON-7732950", "customer-confirmed",
                   "Window, but ahead of the wing.")
    v2 = s.write(t, Draft("seat", "window, ahead of the wing", "standing",
                          later, 0.95,
                          observed_at="2026-05-06T15:03:00-05:00"),
                 expected_head=v1.memory_id)
    say(f"v2 {v2.memory_id} supersedes {v2.supersedes}")
    desk = tok(LATER[2], role="agent-desk")
    for r in s.history(desk, "seat"):
        say(f"  v{r.version} {r.memory_id} {r.status:<10} {r.value}")
    now = [r.value for r in s.read(t, "seat")]
    say(f"agent loop reads: {now}")


# ------------------------------------------------------------- scope
def part_scope() -> None:
    s = new_store()
    t = tok(LATER[2])
    s.write(t, Draft("seat", "window", "standing",
                     Source("CON-7731402", "customer-confirmed"), 0.95))
    s.write(t, Draft("health", "knee, recent surgery", "standing",
                     Source("CON-7731402", "desk-entered"), 0.9))
    s.write(t, Draft("meal", "no preference today", "session",
                     Source("CON-7731403", "customer-stated"), 0.9))
    other = tok(LATER[2], tenant="CUS-020771")
    s.write(other, Draft("seat", "aisle", "standing",
                         Source("CON-7731555", "customer-confirmed"), 0.9))
    try:
        s.read(t, tenant="CUS-020771")
    except OutOfScope as e:
        say(f"read tenant CUS-020771 from {LUCIA}: OutOfScope {e}")
    for role in ("agent-loop", "agent-desk", "privacy-office",
                 "analytics"):
        got = s.read(tok(LATER[2], role=role))
        names = ",".join(r.subject for r in got) or "nothing"
        say(f"  {role:<15} reads {len(got)}: {names}")
    later = tok(LATER[2], n=2)
    say(f"next session reads: "
        f"{','.join(r.subject for r in s.read(later))}")
    closed = s.close_session(t)
    say(f"session closed, session memories deleted: {closed}")


# --------------------------------------------------------- authority
def _control():
    clock = FixedClock(START, step_seconds=1)
    return ControlPlane(load_autonomy(), TrailPlane(World(), clock))


def part_authority(n: int = 200, seed: int = 22) -> None:
    packet = ContextPacket(LATER[2], {
        "voucher_promise": Fact("voucher_promise", 75.0,
                                "memory:MR-00007", START),
        "contact_record": Fact("contact_record", "CON-7730988",
                               "crm-contacts", START)})
    p = Proposal("voucher", LATER[2], 75.0,
                 "desk promised a $75 voucher on the last call")
    c = _control()
    d = c.decide(p, packet)
    pid = d.permission.permission_id if d.permission else "-"
    say(f"control alone:   {d.verdict}, {pid}, {d.reason}")
    c = _control()
    d = authorize(c, p, packet, ["memory:MR-00007"])
    say(f"memory grounds:  {d.verdict} to {d.receiver}, {d.pending_id}")
    say(f"  {d.reason}")
    d = authorize(c, p, packet, ["fact:voucher_promise"])
    say(f"fact from memory: {d.verdict} to {d.receiver}, {d.pending_id}")
    say(f"  {d.reason}")
    d = authorize(c, p, packet, ["fact:contact_record"])
    pid = d.permission.permission_id if d.permission else "-"
    say(f"contact record:  {d.verdict}, {pid}, {d.reason}")
    # Owen's measure: seeded proposals, a third citing memory.
    r = seeded(seed, "memory", "authority")
    c = _control()
    permits = from_memory = cited = 0
    for k in range(n):
        g = ["fact:contact_record"]
        if r.random() < 1 / 3:
            g.append(r.choice(["memory:MR-00007", "fact:voucher_promise"]))
            cited += 1
        usd = round(r.uniform(10, 95), 2)
        d = authorize(c, Proposal("voucher", f"LTG-{6000000 + k}", usd,
                                  "goodwill"), packet, g)
        if d.verdict == "permit":
            permits += 1
            if len(g) > 1:
                from_memory += 1
    say(f"{n} proposals, {cited} citing memory: {permits} permits, "
        f"{from_memory} on memory")


# ------------------------------------------------------------ forget
def _family(s: MemoryStore) -> None:
    t = tok(LATER[2])
    a = s.write(t, Draft("seat", "window", "standing",
                         Source("CON-7731402", "customer-confirmed"), 0.95))
    b = s.write(t, Draft("health", "knee, recent surgery", "standing",
                         Source("CON-7731402", "desk-entered"), 0.9))
    s.write(t, Draft("meal", "vegetarian", "standing",
                     Source("CON-7731410", "customer-confirmed"), 0.9))
    s.write(t, Draft("summary", "window; knee; vegetarian", "standing",
                     Source("CON-7731411", "desk-entered"), 0.8,
                     derived_from=(a.memory_id, b.memory_id)))
    comp = tok(LATER[2], tenant=COMPANION)
    c = s.write(comp, Draft("companion", "seat beside spouse, window",
                            "standing",
                            Source("CON-7731412", "desk-entered"), 0.8,
                            derived_from=(a.memory_id,)))
    s.write(comp, Draft("summary", "beside spouse; window", "standing",
                        Source("CON-7731413", "desk-entered"), 0.8,
                        derived_from=(c.memory_id,)))


def part_forget() -> None:
    s = new_store()
    _family(s)
    gone = naive_forget(s, LUCIA)
    left = remaining(s, LUCIA)
    say(f"delete where tenant = {LUCIA}: {len(gone)} deleted")
    say(f"  still live and made from hers: {len(left)} {left}")
    s = new_store()
    _family(s)
    snap = snapshot(s)
    gone = forget(s, LUCIA)
    say(f"forget through derived_from: {len(gone)} deleted, "
        f"{len(remaining(s, LUCIA))} left")
    say(f"  tombstones written: {len(s.tombstones)}")
    back = restore(s, snap, replay=False)
    say(f"restore backup, no replay: {len(back)} resurrected")
    s2 = new_store()
    _family(s2)
    snap = snapshot(s2)
    forget(s2, LUCIA)
    back = restore(s2, snap, replay=True)
    say(f"restore backup, tombstones first: {len(back)} resurrected")


# ------------------------------------------------------------- audit
def part_audit() -> None:
    from corpus.generate import generate
    a = audit_legacy(generate()["memories"])
    say(f"pilot notes before May 11, 2026: {a['notes']} "
        f"({a['customers']} customers)")
    say(f"  notes with a scope the reader honored: {a['with_scope']}")
    for k, v in a["outcomes"].items():
        say(f"  {k:<13} {v:>4}  {v / a['notes']:5.1%}")
    say(f"  on refund, health, or contact subjects: "
        f"{a['high_consequence']}")


# -------------------------------------------------------------- pack
def part_pack() -> None:
    s = new_store(step=60)
    t = tok(LATER[2], role="agent-loop")
    subjects = [("seat", "window"), ("meal", "vegetarian"),
                ("departure", "mornings"), ("room", "quiet room"),
                ("contact", "not before 9:00 a.m."),
                ("bags", "one checked bag"), ("lounge", "uses lounges"),
                ("car", "compact car")]
    for k in range(64):
        sub, val = subjects[k % len(subjects)]
        s.write(t, Draft(f"{sub}-{k // len(subjects)}" if k >= 8 else sub,
                         val, "standing",
                         Source(f"CON-77{32000 + k}", "customer-confirmed"),
                         0.9))
    items, left = to_items(s.read(t), cap=1_000)
    used = sum(i.tokens for i in items)
    say(f"memories readable: {len(items) + len(left)}, "
        f"slot cap 1,000 tokens")
    say(f"packed {len(items)} whole records, {used} tokens; "
        f"left out {len(left)}")
    say(f"first item: {items[0].text[:57]}")


PARTS = {"pilot": part_pilot, "write": part_write,
         "supersede": part_supersede, "scope": part_scope,
         "authority": part_authority, "forget": part_forget,
         "audit": part_audit, "pack": part_pack}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="memory.demo")
    ap.add_argument("--seed", type=int, default=22)
    ap.add_argument("--part", choices=sorted(PARTS))
    ap.add_argument("--no-provenance", action="store_true")
    a = ap.parse_args(argv)
    if a.no_provenance:
        part_write(no_provenance=True)
        return 0
    parts = [a.part] if a.part else list(PARTS)
    for i, name in enumerate(parts):
        if len(parts) > 1:
            say(f"-- {name} --")
        if name == "authority":
            part_authority(seed=a.seed)
        else:
            PARTS[name]()
        if i < len(parts) - 1:
            say()
    return 0


if __name__ == "__main__":
    sys.exit(main())
