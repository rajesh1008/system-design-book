"""Tests for the chain record and loop. Run: python3 -m unittest chain.test_chain -v"""
import unittest

from .demo import AMOUNT, ITINERARY, full_record, proposal
from .loop import ACTOR, PaymentProcessor, ChainLoop, Trail, naive_refund
from .record import ChainRecord, Permission, Refused


class ChainTests(unittest.TestCase):
    def test_pilot_loop_reproduces_the_double_refund(self):
        net = PaymentProcessor(slow_calls={1})
        naive_refund(net, ITINERARY, AMOUNT)
        self.assertEqual(len(net.settled(ITINERARY)), 2)

    def test_refuses_without_permission_or_key(self):
        net = PaymentProcessor()
        with self.assertRaises(Refused) as ctx:
            ChainLoop(net, Trail()).execute(ChainRecord(proposal=proposal()))
        self.assertEqual(ctx.exception.missing, ["permission", "idempotency_key"])
        self.assertEqual(net.credits, [])

    def test_refuses_permission_granted_by_the_actor(self):
        rec = full_record()
        rec.permission = Permission("PRM-1", ACTOR, "refunds-v3", 1500.0)
        with self.assertRaises(Refused):
            ChainLoop(PaymentProcessor(), Trail()).execute(rec)

    def test_refuses_amount_above_permission(self):
        rec = full_record(amount=2000.0)
        net = PaymentProcessor()
        with self.assertRaises(Refused):
            ChainLoop(net, Trail()).execute(rec)
        self.assertEqual(net.credits, [])

    def test_full_record_survives_timeout_with_one_credit(self):
        net = PaymentProcessor(slow_calls={1})
        rec = ChainLoop(net, Trail()).execute(full_record())
        self.assertEqual(len(net.settled(ITINERARY)), 1)
        self.assertTrue(rec.verification["ok"])
        self.assertIsNotNone(rec.trail_entry)

    def test_refuses_verification_by_the_actor(self):
        bad = lambda n, r: {"verified_by": ACTOR, "credits_found": 1, "ok": True}
        with self.assertRaises(Refused) as ctx:
            ChainLoop(PaymentProcessor(), Trail(), verifier=bad).execute(full_record())
        self.assertIn("independent verification", ctx.exception.missing)

    def test_unanswered_effect_is_not_counted_done(self):
        net = PaymentProcessor(lost_calls={1, 2, 3})
        with self.assertRaises(Refused) as ctx:
            ChainLoop(net, Trail()).execute(full_record())
        self.assertIn("execution", ctx.exception.missing)

    def test_trail_is_hash_linked(self):
        trail = Trail()
        loop = ChainLoop(PaymentProcessor(), trail)
        loop.execute(full_record("LTG-1"))
        loop.execute(full_record("LTG-2", pid="PRM-2"))
        self.assertIn('"prev": "genesis"', trail.lines[0])
        self.assertNotIn('"prev": "genesis"', trail.lines[1])


if __name__ == "__main__":
    unittest.main()
