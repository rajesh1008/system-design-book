"""Chapter 32 lab.

    python3 -m identity.demo --part found      # June 16 access review
    python3 -m identity.demo --part mint       # one run, one refund
    python3 -m identity.demo --part probes     # what the token refuses
    python3 -m identity.demo --part broker     # keys stay out of context
    python3 -m identity.demo --part data       # data classes, replayed
    python3 -m identity.demo --part exposure [--median 45]
    python3 -m identity.demo --part inject     # a standing write key
    python3 -m identity.demo --part check      # the trail check
"""
from __future__ import annotations

import argparse
import base64
import json

from common.text import emit

from . import check as trailcheck
from . import exposure, pii, standing
from .broker import BrokerRefused
from .delegate import Refused, attenuate
from .gate import SessionGateway
from .lab import CUSTOMER, OTHER_TRIP, REFUND, TICKET, TRIP, build_id
from .tokens import encode

PERM = "perm-0622-001"
GRANT = {"booking_read", "fare_calc", "refund_ticket", "customer_notify"}


def claims_of(token: str) -> dict:
    body = token.split(".")[0]
    return json.loads(base64.urlsafe_b64decode(body + "=" *
                                               (-len(body) % 4)))


def part_found() -> int:
    cred = standing.AS_FOUND[0]
    used = standing.usage()
    r = standing.review(cred, used)
    emit(f"credential: {cred.name}, held by {cred.holder}")
    emit(f"issued {cred.issued}, rotated never, "
         f"age {cred.age_days('2026-06-16')} days, expires never")
    emit(f"scopes granted {r['granted']}, exercised in 30 days "
         f"{r['exercised']}")
    for s in standing.SCOPES:
        emit(f"  {s:<16}{used[s]:>7,}")
    emit(f"never exercised: {', '.join(r['never'])}")
    fails = standing.identity_test(standing.AS_FOUND, "2026-06-16")
    emit(f"identity test: {'pass' if not fails else 'FAIL'}")
    for f in fails:
        emit(f"  {f}")
    return 0


def part_mint() -> int:
    w = build_id()
    run = w.new_run()
    tok = w.cp.delegate(w.session, w.agent, run, TRIP, GRANT)
    c = claims_of(tok)
    emit(f"run token, {len(tok)} characters, signed by {c['iss']}")
    emit(f"  sub (customer)   {c['sub']}")
    emit(f"  act (agent)      {c['act']['sub']}")
    emit(f"  run              {c['run']}")
    emit(f"  itinerary        {c['itinerary']}")
    emit(f"  tools            {', '.join(c['tools'][:2])},")
    emit(f"                   {', '.join(c['tools'][2:])}")
    emit(f"  lifetime         {int(c['exp'] - c['iat'])} s")
    w.base.policy.issue(PERM, "refund_ticket", REFUND)
    r = w.gw.call_as(tok, "booking", "booking_read",
                     {"booking_ref": TRIP})
    emit(f"booking_read {TRIP}: {'allowed' if r.ok else r.reason}")
    r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=PERM)
    emit(f"refund_ticket {TICKET} $250.00 with {PERM}: "
         f"{'allowed' if r.ok else r.reason}")
    line = json.loads(w.gw.trail.lines[-1])
    emit("trail line:")
    for k in ("user", "agent", "run", "perm", "args_digest"):
        emit(f"  {k:<12}{line[k]}")
    emit(f"  {'sig':<12}{line['sig'][:24]}...")
    emit("payments system of record saw:")
    for verdict, obo, tool in w.broker.sor["payments"].log:
        emit(f"  {verdict} {tool}, {obo}")
    return 0


def part_probes() -> int:
    w = build_id()
    run = w.new_run()
    tok = w.cp.delegate(w.session, w.agent, run, TRIP, GRANT)
    other = dict(REFUND, itinerary_id=OTHER_TRIP)
    w.base.policy.issue("perm-0622-002", "refund_ticket", other)
    now = w.base.clock.now().timestamp()
    reader = encode(attenuate(claims_of_obj(tok), {"booking_read"},
                              300, now))
    imp = w.cp.impersonate(w.session, TRIP, GRANT)
    body, sig = tok.split(".")
    c = claims_of(tok)
    c["itinerary"] = OTHER_TRIP
    forged = base64.urlsafe_b64encode(json.dumps(
        c, sort_keys=True).encode()).decode().rstrip("=") + "." + sig
    probes = [
        ("refund another trip", tok, other, "perm-0622-002"),
        ("forged itinerary claim", forged, other, "perm-0622-002"),
        ("child token, read only", reader, REFUND, PERM),
        ("impersonation token", imp, REFUND, PERM),
        ("standing account", "svc-agent-gw", REFUND, PERM),
    ]
    w.base.policy.issue(PERM, "refund_ticket", REFUND)
    emit(f"{'probe':<28}result")
    for name, t, args, perm in probes:
        r = w.gw.call_as(t, "payments", "refund_ticket", args,
                         permission=perm)
        emit(f"{name:<28}{'allowed' if r.ok else r.reason}")
    for name, fn in (("widen the child", lambda: attenuate(
            claims_of_obj(reader), GRANT, 60, now)),
            ("mint for another's trip", lambda: w.cp.delegate(
                w.session, w.agent, run, OTHER_TRIP, GRANT)),
            ("mint for one hour", lambda: w.cp.delegate(
                w.session, w.agent, run, TRIP, GRANT, ttl_s=3600))):
        try:
            fn()
            emit(f"{name:<28}minted")
        except Refused as e:
            emit(f"{name:<28}{e.reason}")
    w.base.clock.advance(901)
    r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=PERM)
    emit(f"{'same token, 15 min later':<28}{r.reason or 'allowed'}")
    w2 = build_id()
    t2 = w2.cp.delegate(w2.session, w2.agent, w2.new_run(), TRIP, GRANT)
    w2.base.policy.issue(PERM, "refund_ticket", REFUND)
    w2.verifier.revoked.add(claims_of(t2)["run"])
    r = w2.gw.call_as(t2, "payments", "refund_ticket", REFUND,
                      permission=PERM)
    emit(f"{'run revoked mid-case':<28}{r.reason or 'allowed'}")
    r = w2.gw.call_as(t2, "booking", "booking_read",
                      {"booking_ref": TRIP})
    emit(f"{'  then a read':<28}{r.reason or 'allowed'}")
    paid = w.broker.sor["payments"].log + w2.broker.sor["payments"].log
    emit(f"refunds the payments system received: {len(paid)}")
    return 0


def claims_of_obj(token: str):
    from .tokens import Claims
    return Claims.from_dict(claims_of(token))


def part_broker() -> int:
    w = build_id()
    tok = w.cp.delegate(w.session, w.agent, w.new_run(), TRIP, GRANT)
    w.base.policy.issue(PERM, "refund_ticket", REFUND)
    r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=PERM)
    keys = list(w.broker._keys.values())
    back = sum(k in json.dumps(r.for_model()) for k in keys)
    emit(f"keys held by the broker: {', '.join(w.broker.held())}")
    emit(f"keys filled: {w.broker.fills}; in the result to the run: "
         f"{back}")
    leaks = sum(any(k in ln for k in keys) for ln in w.gw.trail.lines)
    emit(f"trail lines containing a held key: {leaks} of "
         f"{len(w.gw.trail.lines)}")
    cases = [("clean case summary", f"Refund {TICKET} on {TRIP}."),
             ("supplier key pasted in a note",
              f"Supplier said use {w.broker._keys['bookings']}"),
             ("run token in a tool result", f"debug: token={tok}")]
    emit("context assembler, before the model call:")
    for name, text in cases:
        found = w.broker.scan_context(text)
        emit(f"  {name:<32}"
             f"{'refused: ' + found[0] if found else 'passes'}")
    try:
        w.broker.fill(claims_of_obj(tok), "payments", "refund_ticket",
                      dict(REFUND, itinerary_id=OTHER_TRIP))
    except BrokerRefused as e:
        emit(f"broker asked for another trip's refund: {e.reason}")
    return 0


def part_data() -> int:
    emit(f"{'200 seeded cases':<24}{'card':>6}{'document':>10}"
         f"{'contact':>9}")
    for label, fixed, loose in (("as found (June 16)", False, False),
                                ("classes applied", True, False),
                                ("loose shapes (June 26)", True, True)):
        r = pii.replay(fixed=fixed, loose=loose)
        h = r["hits"]
        emit(f"{label:<24}{h['card']:>6}{h['identity_document']:>10}"
             f"{h['contact']:>9}")
    r = pii.replay(fixed=True)
    emit("raw values the seeded search found with classes applied:")
    for case in r["missed"]:
        rec, _ = pii.case_record(int(case[3:]) - 620000)
        emit(f"  {case}: {rec['note'][:44]}")
    emit("retention by class (days, outside its own vault):")
    for cls, days in pii.RETENTION_DAYS.items():
        emit(f"  {cls:<20}{days:>4}")
    return 0


def part_exposure(median: float) -> int:
    emit(f"1,000 leaked tokens, found after a median {median:g} min")
    emit(f"{'lifetime':<12}{'reach':<14}{'worked':>8}"
         f"{'usable min':>12}{'itin-min':>14}")
    for row in exposure.table(median):
        m = row["lifetime_min"]
        standing_ = m == exposure.STANDING_MIN
        life = "225 days" if standing_ else (
            "1 day" if m == 1440 else f"{m:g} min")
        reach = "every trip" if standing_ else "1 itinerary"
        tot = row["accepted"] * row["usable_min"]
        im = "unbounded" if standing_ else f"{tot:,.0f}"
        emit(f"{life:<12}{reach:<14}{row['accepted']:>8}"
             f"{row['usable_min']:>12,.1f}{im:>14}")
    return 0


def part_inject() -> int:
    inv = standing.after_fix()
    fails = standing.identity_test(inv, "2026-06-22")
    emit(f"inventory June 22: {len(inv)} credentials, identity test "
         f"{'pass' if not fails else 'FAIL'}")
    inj = standing.INJECTED
    emit(f"injected: {inj.name}, {', '.join(inj.scopes)}, "
         f"{int(inj.lifetime_s // 86400)} days")
    fails = standing.identity_test(inv + [inj], "2026-06-22")
    emit(f"identity test: {'pass' if not fails else 'FAIL'}")
    for f in fails:
        emit(f"  {f}")
    w = build_id()
    w.base.policy.issue(PERM, "refund_ticket", REFUND)
    r = w.gw.call_as(f"{inj.name}:lab-credential", "payments",
                     "refund_ticket", REFUND, permission=PERM)
    emit(f"gateway shown {inj.name}: {r.reason}")
    n = w.base.servers["payments"].requests
    emit(f"payments requests: {n}")
    caught = bool(fails) and not r.ok and n == 0
    emit(f"injection {'caught' if caught else 'NOT caught'}")
    return 0 if caught else 1


def part_check() -> int:
    w = build_id()
    for i in range(3):
        tok = w.cp.delegate(w.session, w.agent, w.new_run(), TRIP,
                            GRANT)
        perm = f"perm-0622-1{i:02d}"
        w.base.policy.issue(perm, "refund_ticket", REFUND)
        w.gw.call_as(tok, "booking", "booking_read",
                     {"booking_ref": TRIP})
        w.gw.call_as(tok, "fares", "fare_calc",
                     {"ticket_number": TICKET})
        w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=perm)
        w.gw.call_as(tok, "payments", "refund_ticket",
                     dict(REFUND, itinerary_id=OTHER_TRIP),
                     permission=perm)
    w.gw.call_as("svc-agent-gw", "booking", "booking_read",
                 {"booking_ref": TRIP})
    ours = trailcheck.check(w.gw.trail.lines)
    old = build_id().base
    old.policy.issue(PERM, "refund_ticket", REFUND)
    sg = SessionGateway(old.registry, old.servers, old.callers,
                        old.policy, old.trail, old.clock,
                        session=(CUSTOMER, "agent:servicing@1.0.0",
                                 "CASE-77310"))
    sg.call("wl-servicing-agent", "payments", "refund_ticket", REFUND,
            permission=PERM)
    theirs = trailcheck.check(old.trail.lines)
    for label, r in (("identity gateway", ours),
                     ("June 16 gateway", theirs)):
        calls = "call" if r["lines"] == 1 else "calls"
        emit(f"{label}: {r['lines']} tool {calls}, three identities "
             f"{r['three_ids']}, signed {r['signed']}")
        emit(f"  effects allowed {r['effects_allowed']}, bound "
             f"{r['effects_bound']}; refused unknown "
             f"{r['refused_unknown']}; chain "
             f"{'intact' if not r['chain'] else 'broken'}")
        for p in r["problems"]:
            emit(f"  problem: {p}")
    lines = list(w.gw.trail.lines)
    i = next(n for n, ln in enumerate(lines)
             if json.loads(ln)["event"] == "tool_call")
    e = json.loads(lines[i])
    e["user"] = "C-990001"
    lines[i] = json.dumps(e, sort_keys=True)
    r = trailcheck.check(lines)
    emit("one line's customer edited after the fact:")
    emit(f"  {r['problems'][0]}")
    emit(f"  chain: {r['chain'][0] if r['chain'] else 'intact'}")
    return 0 if not ours["problems"] else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True,
                    choices=["found", "mint", "probes", "broker", "data",
                             "exposure", "inject", "check"])
    ap.add_argument("--median", type=float, default=45.0)
    a = ap.parse_args(argv)
    if a.part == "exposure":
        return part_exposure(a.median)
    return globals()[f"part_{a.part}"]()


if __name__ == "__main__":
    raise SystemExit(main())
