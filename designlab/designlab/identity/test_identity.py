"""Chapter 32 tests: run identity, delegation, broker, data classes."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from common.redact import find_secrets
from common.text import too_long

from . import check, demo, exposure, pii, standing
from .broker import BrokerRefused
from .delegate import Refused, attenuate
from .lab import OTHER_TRIP, REFUND, TRIP, build_id
from .tokens import RUN_TTL_S, Verifier, encode

GRANT = demo.GRANT
PERM = demo.PERM


def world_with_token(tools=GRANT):
    w = build_id()
    tok = w.cp.delegate(w.session, w.agent, w.new_run(), TRIP, tools)
    w.base.policy.issue(PERM, "refund_ticket", REFUND)
    return w, tok


class TestTokens(unittest.TestCase):
    def test_claims_carry_three_identities(self):
        _, tok = world_with_token()
        c = demo.claims_of(tok)
        self.assertEqual(c["sub"], "C-118204")
        self.assertEqual(c["act"]["sub"],
                         "agent:servicing@servicing-1.0.0")
        self.assertTrue(c["run"].startswith("run-20260622T"))

    def test_lifetime_is_the_permission_window(self):
        _, tok = world_with_token()
        c = demo.claims_of(tok)
        self.assertEqual(c["exp"] - c["iat"], RUN_TTL_S)
        self.assertEqual(RUN_TTL_S, 900)

    def test_expired_token_refused(self):
        w, tok = world_with_token()
        w.base.clock.advance(RUN_TTL_S + 1)
        r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                         permission=PERM)
        self.assertEqual(r.reason, "expired")
        line = json.loads(w.gw.trail.lines[-1])
        self.assertEqual(line["user"], "C-118204")

    def test_tampered_token_refused(self):
        w, tok = world_with_token()
        body, sig = tok.split(".")
        r = w.gw.call_as(body + "." + sig[::-1], "booking",
                         "booking_read", {"booking_ref": TRIP})
        self.assertEqual(r.reason, "bad_signature")

    def test_wrong_audience_refused(self):
        w, tok = world_with_token()
        v = Verifier(audience="ledger.lakeshore.internal")
        self.assertEqual(v.check(tok, 0).reason, "wrong_audience")

    def test_revoked_run_refused(self):
        w, tok = world_with_token()
        w.verifier.revoked.add(demo.claims_of(tok)["run"])
        r = w.gw.call_as(tok, "booking", "booking_read",
                         {"booking_ref": TRIP})
        self.assertEqual(r.reason, "revoked")


class TestDelegation(unittest.TestCase):
    def test_refund_allowed_and_bound(self):
        w, tok = world_with_token()
        r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                         permission=PERM)
        self.assertTrue(r.ok)
        line = json.loads(w.gw.trail.lines[-1])
        self.assertEqual(line["perm"], PERM)
        self.assertEqual(line["user"], "C-118204")

    def test_other_itinerary_refused(self):
        w, tok = world_with_token()
        other = dict(REFUND, itinerary_id=OTHER_TRIP)
        w.base.policy.issue("p2", "refund_ticket", other)
        r = w.gw.call_as(tok, "payments", "refund_ticket", other,
                         permission="p2")
        self.assertEqual(r.reason, "wrong_itinerary")
        self.assertEqual(w.base.servers["payments"].requests, 0)

    def test_cannot_mint_for_trip_customer_does_not_own(self):
        w, _ = world_with_token()
        with self.assertRaises(Refused) as e:
            w.cp.delegate(w.session, w.agent, "run-x", OTHER_TRIP, GRANT)
        self.assertEqual(e.exception.reason, "not_customers_itinerary")

    def test_cannot_mint_unreviewed_tool(self):
        w, _ = world_with_token()
        with self.assertRaises(Refused):
            w.cp.delegate(w.session, w.agent, "run-x", TRIP,
                          {"points_balance"})

    def test_cannot_mint_longer_than_window(self):
        w, _ = world_with_token()
        with self.assertRaises(Refused):
            w.cp.delegate(w.session, w.agent, "run-x", TRIP, GRANT,
                          ttl_s=3600)

    def test_attenuation_narrows_only(self):
        _, tok = world_with_token()
        parent = demo.claims_of_obj(tok)
        child = attenuate(parent, {"booking_read"}, 60, parent.iat)
        self.assertEqual(child.act, parent.act)
        self.assertLessEqual(child.exp, parent.exp)
        with self.assertRaises(Refused):
            attenuate(child, set(GRANT), 30, parent.iat)
        with self.assertRaises(Refused):
            attenuate(parent, {"booking_read"}, RUN_TTL_S * 2,
                      parent.iat)

    def test_child_cannot_refund(self):
        w, tok = world_with_token()
        p = demo.claims_of_obj(tok)
        child = encode(attenuate(p, {"booking_read"}, 60, p.iat))
        r = w.gw.call_as(child, "payments", "refund_ticket", REFUND,
                         permission=PERM)
        self.assertEqual(r.reason, "not_in_run_scope")

    def test_impersonation_token_refused(self):
        w, _ = world_with_token()
        imp = w.cp.impersonate(w.session, TRIP, GRANT)
        r = w.gw.call_as(imp, "payments", "refund_ticket", REFUND,
                         permission=PERM)
        self.assertEqual(r.reason, "not_a_run_token")


class TestBroker(unittest.TestCase):
    def test_keys_never_reach_trail_or_result(self):
        w, tok = world_with_token()
        r = w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                         permission=PERM)
        keys = list(w.broker._keys.values())
        blob = "\n".join(w.gw.trail.lines) + json.dumps(r.for_model())
        self.assertFalse(any(k in blob for k in keys))
        self.assertEqual(w.broker.fills, 1)

    def test_system_of_record_sees_run_and_customer(self):
        w, tok = world_with_token()
        w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=PERM)
        verdict, obo, _ = w.broker.sor["payments"].log[-1]
        self.assertEqual(verdict, "ok")
        self.assertIn("for C-118204", obo)

    def test_broker_refuses_without_identity(self):
        w, _ = world_with_token()
        with self.assertRaises(BrokerRefused):
            w.broker.fill(None, "payments", "refund_ticket", REFUND)

    def test_secret_in_context_refused(self):
        w, tok = world_with_token()
        self.assertTrue(w.broker.scan_context(
            "note " + w.broker._keys["profiles"]))
        self.assertTrue(w.broker.scan_context(tok))
        self.assertFalse(w.broker.scan_context("Refund TKT-40210."))


class TestStanding(unittest.TestCase):
    def test_as_found_fails_identity_test(self):
        self.assertTrue(standing.identity_test(standing.AS_FOUND,
                                               "2026-06-16"))

    def test_three_scopes_never_exercised(self):
        r = standing.review(standing.AS_FOUND[0], standing.usage())
        self.assertEqual(r["exercised"], 5)
        self.assertEqual(len(r["never"]), 3)

    def test_after_fix_passes_and_injection_fails(self):
        inv = standing.after_fix()
        self.assertEqual(standing.identity_test(inv, "2026-06-22"), [])
        fails = standing.identity_test(inv + [standing.INJECTED],
                                       "2026-06-22")
        self.assertEqual(len(fails), 1)
        self.assertIn("svc-batch-refunds", fails[0])

    def test_stale_broker_key_fails(self):
        inv = standing.after_fix()
        self.assertTrue(standing.identity_test(inv, "2026-08-01"))


class TestData(unittest.TestCase):
    def test_luhn(self):
        self.assertTrue(pii.luhn_ok("4111111111111111"))
        self.assertFalse(pii.luhn_ok("4111111111111112"))

    def test_classes_keep_card_and_contact_out(self):
        r = pii.replay(fixed=True)
        self.assertEqual(r["hits"]["card"], 0)
        self.assertEqual(r["hits"]["contact"], 0)

    def test_seeded_search_finds_what_scanner_missed(self):
        r = pii.replay(fixed=True)
        self.assertEqual(r["hits"]["identity_document"],
                         len(r["missed"]))
        self.assertGreater(len(r["missed"]), 0)

    def test_loose_shapes_close_the_gap(self):
        r = pii.replay(fixed=True, loose=True)
        self.assertEqual(r["hits"], {"card": 0, "identity_document": 0,
                                     "contact": 0})

    def test_as_found_leaks_every_class(self):
        h = pii.replay(fixed=False)["hits"]
        self.assertEqual(h["card"], 200)
        self.assertGreater(h["identity_document"], 0)

    def test_vault_resolves_only_for_purpose(self):
        v = pii.Vault()
        ref = v.tokenize("card", "4111111111111111")
        self.assertIsNone(v.resolve(ref, "model_context"))
        self.assertEqual(v.resolve(ref, "processor_refund"),
                         "4111111111111111")


class TestTrailAndDemo(unittest.TestCase):
    def test_trail_check_passes_and_catches_edit(self):
        w, tok = world_with_token()
        w.gw.call_as(tok, "payments", "refund_ticket", REFUND,
                     permission=PERM)
        r = check.check(w.gw.trail.lines)
        self.assertEqual(r["problems"], [])
        self.assertEqual(r["three_ids"], r["lines"])
        lines = list(w.gw.trail.lines)
        e = json.loads(lines[-1])
        e["agent"] = "agent:desk@pilot"
        lines[-1] = json.dumps(e, sort_keys=True)
        self.assertTrue(check.check(lines)["problems"])

    def test_shorter_life_less_exposure(self):
        a = exposure.simulate(15)["accepted"]
        b = exposure.simulate(60)["accepted"]
        self.assertLess(a, b / 4)

    def test_demo_parts_fit_and_hold_no_secrets(self):
        for part in ("found", "mint", "probes", "broker", "data",
                     "exposure", "inject", "check"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = demo.main(["--part", part])
            self.assertEqual(code, 0, part)
            self.assertEqual(too_long(buf.getvalue()), [], part)
            self.assertEqual(find_secrets(buf.getvalue()), [], part)


if __name__ == "__main__":
    unittest.main()
