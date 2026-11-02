"""Chapter 24 lab: the stale memory, injected and fixed.

    python3 -m knowops.demo                  # the fall and the fix
    python3 -m knowops.demo --no-verifier    # outcome check vs proposal
    python3 -m knowops.demo --ttl 365        # destination TTL in days
    python3 -m knowops.demo --weekly         # fresh sample vs golden
    python3 -m knowops.demo --weekly --age-index   # frozen index

Offline, seeded, no key needed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime

from common.clock import FixedClock
from common.text import emit
from common.trail import TrailWriter
from corpus.fall2 import (CITY, DETECT_AT, EVENT_ID, GOODWILL_USD,
                          LAST_FIXED, NOTE_ID, CDT, generate_fall2)
from memory import Draft, MemoryStore, SessionToken, Source, by_record

from . import audit, card
from .expiry import RETENTION_V2, review_legacy
from .pilot import fixed_choice, packet, replay_choice, where
from .verify import destination_verifier, pnr_reconciler

SCORE_TASKS = 31_500          # agent plus assisted, May 2026
MAY_RATE = 99.1


def hm(t: int) -> str:
    h, m = t // 3600, t % 3600 // 60
    return f"{h % 12 or 12}:{m:02d} {'a.m.' if h < 12 else 'p.m.'}"


def show_note(t) -> None:
    n = t["fall2_note"][0]
    emit(f"{n['memory_id']}  customer {n['customer_id']}")
    emit(f"  fact: {n['fact']!r}  subject: {n['subject']}  "
         f"scope: {n['scope']}")
    emit(f"  created {n['created_at']}")
    emit(f"  expires {n['expires_at']}  enforced: "
         f"{n['expiry_enforced']}")
    first, rest = n["provenance"]["quote"].split("; ")
    emit(f"  quote: {first};")
    emit(f"         {rest}")


def show_packet(t) -> None:
    it = t["fall2_itins"][0]
    for mode in ("pilot", "fixed"):
        asm = packet(it, mode)
        emit(f"{mode}: {asm.tokens:,} tokens")
        for needle in (CITY, "prefers Denver", "destination of record"):
            hits = where(asm, needle)
            if hits:
                at = ", ".join(f"{s} @{o:,}" for s, o in hits)
                emit(f"  {needle!r:<24} {at}")
        pick = replay_choice if mode == "pilot" else fixed_choice
        flight, why = pick(it, asm)
        emit(f"  choice: {flight} ({why})")


def outcomes(t, verifier: bool = True):
    itins = {i["itinerary_id"]: i for i in t["fall2_itins"]}
    opts = {o["flight"]: o for o in t["fall2_options"]}
    pnr_ok = dest_ok = wrong = 0
    for r in t["fall2_runs"]:
        if r["disposition"] != "rebooked":
            continue
        airline = {"flight": r["proposal"],
                   "destination": opts[r["proposal"]]["destination"]}
        prop = {"flight": r["proposal"], "destination": r["proposal_dest"]}
        pnr_ok += pnr_reconciler(prop, airline)
        v = destination_verifier(itins[r["itinerary_id"]], airline)
        dest_ok += v == "verified"
        wrong += v == "wrong-destination"
    return pnr_ok, dest_ok, wrong


def show_verify(t, verifier: bool) -> None:
    pnr_ok, dest_ok, wrong = outcomes(t)
    n = pnr_ok
    emit(f"rebookings on {EVENT_ID}: {n:,}")
    emit(f"  pnr-reconciler (airline = proposal):  {pnr_ok:,} verified")
    if verifier:
        emit(f"  destination verifier (airline = ticketed):")
        emit(f"      {dest_ok:,} verified, {wrong} wrong-destination")
    rate_record = MAY_RATE - 100.0 * wrong / SCORE_TASKS
    emit(f"  May card, verified-outcome rate:  {MAY_RATE:.1f}%")
    if verifier:
        emit(f"  same month, checked against the ticket:  "
             f"{rate_record:.2f}%")
    else:
        emit("  wrong cities the card can see:  0")


def show_trail(t) -> None:
    used = audit.used_memory(t["fall2_runs"], NOTE_ID)
    d = audit.dispositions(used)
    emit(f"packets carrying {NOTE_ID}: {len(used)} "
         f"({d['rebooked']} rebooked, {d['refusal']} held)")
    wrong = audit.wrong_city(t["fall2_runs"], t["fall2_itins"])
    emit(f"runs proposing a city not on the itinerary: {len(wrong)}")
    hist = t["fall2_history"]
    places = audit.place_notes(hist)
    mine = [h for h in hist if h["note_id"] == NOTE_ID]
    bad = [h for h in hist if h["final_dest"] != h["itinerary_dest"]]
    emit(f"earlier runs with a place note (Nov 3 to May 18): "
         f"{len(places)}")
    emit(f"  carrying {NOTE_ID}: {len(mine)}; pinned: "
         f"{sum(h['pinned'] for h in hist)}; wrong city: {len(bad)}")


def show_recovery(t) -> None:
    rec = t["fall2_recovery"]
    s = Counter(r["status_at_detection"] for r in rec)
    emit(f"at {hm(DETECT_AT)}: {s['not-traveled']} not yet traveled, "
         f"{s['checked-in']} checked in")
    gate = sum(r["stopped_at_gate"] for r in rec)
    emit(f"  checked in, reached before boarding: {gate}; flew to "
         f"Denver: {s['checked-in'] - gate}")
    routes = Counter(r["route"] for r in rec)
    emit(f"  to Phoenix: {routes['morning']} Wed morning, "
         f"{routes['afternoon']} Wed afternoon, {routes['via-DEN']} via "
         f"Denver")
    last = max(r["arrived_phx"] for r in rec)
    mins = (24 * 3600 + LAST_FIXED - DETECT_AT) // 60
    emit(f"  last arrival {last}")
    emit(f"  detection to last correction: {mins // 60} h {mins % 60} m")
    cost = sum(r["goodwill_usd"] + r["hotel_usd"] + r["onward_usd"]
               for r in rec)
    emit(f"  goodwill {len(rec)} x ${GOODWILL_USD:.0f}; total "
         f"${cost:,.2f}")


def show_fix(t, ttl: int) -> None:
    note = t["fall2_note"][0]
    now = datetime(2026, 5, 19, 11, 31, tzinfo=CDT)
    it = t["fall2_itins"][0]
    booking = {"record_id": it["itinerary_id"],
               "destination": it["destination"], "origin": it["origin"]}
    emit("memory-retention-v2, legacy note on May 19:")
    emit(f"  without the record: {review_legacy(note, now)[0]}")
    emit(f"  with the record:    {review_legacy(note, now, booking)[0]}")
    clock = FixedClock("2026-05-19T11:00:00-05:00")
    trail = TrailWriter(clock=clock)
    ttls = dict(RETENTION_V2, destination=ttl)
    store = MemoryStore(clock, trail, ttl_days=ttls)
    tok = SessionToken("SES-0519-1", it["customer_id"], it["itinerary_id"])
    said = Source("CON-6610932", "customer-confirmed",
                  "Yes, Denver from now on")
    rec = store.write(tok, Draft("destination", "Denver", "standing",
                                 said, 0.7))
    emit(f"governed write, destination TTL {ttl} days:")
    emit(f"  expires {rec.expires_at}")
    later = (datetime.fromisoformat(rec.expires_at)
             - datetime.fromisoformat(rec.recorded_at)).days
    emit(f"  readable for {later} days")
    kept, dropped = by_record(store.read(tok), booking, trail)
    for r, subj, val in dropped:
        emit(f"  superseded at read: {subj} {r.value!r} -> record {val}")
    emit(f"  kept in the packet: {len(kept)}")


def show_replay(t) -> None:
    acct = [i for i in t["fall2_itins"] if i["account"]]
    for mode, pick in (("pilot", replay_choice), ("fixed", fixed_choice)):
        to = Counter()
        for it in acct:
            asm = packet(it, mode)
            f, _ = pick(it, asm)
            to["DEN" if f in ("XPA0842", "XPA0916", "XPA0730")
               else "PHX"] += 1
        emit(f"{mode}: {len(acct)} travelers -> PHX {to['PHX']}, "
             f"DEN {to['DEN']}")


def show_weekly(policy: str) -> None:
    from .weekly import run
    emit(f"index policy: {policy}")
    emit(f"{'week of':<12}{'golden':>8}{'fresh':>8}{'gap':>7}"
         f"{'misses':>8}  slice   alert")
    for r in run(policy):
        emit(f"{r['week'].isoformat():<12}{r['golden']:>7.1f}%"
             f"{r['fresh']:>7.1f}%{r['gap']:>7.1f}{r['missed']:>8}  "
             f"{r['slice'] or '-':<8}{'ALERT' if r['alert'] else ''}"
             .rstrip())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="knowops.demo")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--no-verifier", action="store_true")
    ap.add_argument("--ttl", type=int, default=RETENTION_V2["destination"])
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--age-index", action="store_true")
    a = ap.parse_args(argv)
    if a.weekly:
        show_weekly("frozen" if a.age_index else "nightly")
        if not a.age_index:
            emit()
            show_weekly("contract")
        return 0
    t = generate_fall2(a.seed)
    if a.no_verifier:
        show_verify(t, verifier=False)
        return 0
    if a.ttl != RETENTION_V2["destination"]:
        show_fix(t, a.ttl)
        return 0
    for title, fn in (("the note", show_note),
                      ("the packet, 11:31 a.m.", show_packet),
                      ("verification", lambda x: show_verify(x, True)),
                      ("the trail search, 3:20 p.m.", show_trail),
                      ("recovery", show_recovery),
                      ("the fix", lambda x: show_fix(x, a.ttl)),
                      ("replay, the account's 41", show_replay)):
        emit(f"-- {title} --")
        fn(t)
        emit()
    emit("knowledge operations scorecard, week of June 1:")
    for ln in card.lines():
        emit(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
