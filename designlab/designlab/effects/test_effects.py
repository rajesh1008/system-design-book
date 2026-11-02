import unittest

from chain.record import Permission
from corpus.tools import SupplierSim, spec
from effects import replay, saga
from effects.execute import Executor
from effects.keys import KeyIssuer, KeyRefused
from effects.ledger import BadMove, Ledger, LedgerConflict, StaleLease

P = Permission("PRM-1", "policy-engine", "lab", 1500.0)
REQ = {"intent": "I1", "target": "LTG-1", "amount_usd": 412.60}


class KeyTest(unittest.TestCase):
    def test_same_permission_same_key(self):
        k = KeyIssuer()
        self.assertEqual(k.mint(P, "processor-refund", REQ).key,
                         k.mint(P, "processor-refund", REQ).key)

    def test_new_permission_new_key(self):
        k = KeyIssuer()
        p2 = Permission("PRM-2", "policy-engine", "lab", 1500.0)
        self.assertNotEqual(k.mint(P, "processor-refund", REQ).key,
                            k.mint(p2, "processor-refund", REQ).key)

    def test_permission_cannot_cover_other_request(self):
        k = KeyIssuer()
        k.mint(P, "processor-refund", REQ)
        with self.assertRaises(KeyRefused):
            k.mint(P, "processor-refund", dict(REQ, amount_usd=1.0))

    def test_no_permission_no_key(self):
        with self.assertRaises(KeyRefused):
            KeyIssuer().mint(None, "processor-refund", REQ)


class LedgerTest(unittest.TestCase):
    def test_conflict_on_fingerprint(self):
        led, ek = Ledger(), KeyIssuer().mint(P, "processor-refund", REQ)
        led.reserve(ek, 0.0)
        bad = type(ek)(ek.key, ek.permission_id, ek.tool, "x", 0.0)
        with self.assertRaises(LedgerConflict):
            led.reserve(bad, 0.0)

    def test_illegal_move(self):
        led, ek = Ledger(), KeyIssuer().mint(P, "processor-refund", REQ)
        led.reserve(ek, 0.0)
        with self.assertRaises(BadMove):
            led.move(ek.key, "committed", 0.0)

    def test_stale_lease_refused(self):
        led, ek = Ledger(), KeyIssuer().mint(P, "airline-rebook-a", REQ)
        led.reserve(ek, 0.0)
        a = led.acquire(ek.key, "a", 0.0, ttl=30)
        b = led.acquire(ek.key, "b", 60.0, ttl=30)
        led.move(ek.key, "attempting", 60.0, "", b)
        with self.assertRaises(StaleLease):
            led.move(ek.key, "unknown", 70.0, "", a)


class ExecutorTest(unittest.TestCase):
    def run_one(self, tool, faults=None, lag=0.0, stock=0):
        sim = SupplierSim(spec(tool), faults=faults or {})
        if stock:
            sim.stock("LTG-1", stock)
        ek = KeyIssuer().mint(P, tool, REQ)
        ex = Executor(Ledger(), {tool: sim}, lags=lambda _: lag)
        return ex.run(ek, REQ), sim, ex

    def test_native_timeout_replays_key(self):
        e, sim, _ = self.run_one("processor-refund", {1: "late"})
        self.assertEqual((e.state, len(sim.records)), ("committed", 1))

    def test_lookup_finds_late_effect(self):
        e, sim, _ = self.run_one("airline-rebook-b", {1: "late"}, lag=22)
        self.assertEqual((e.state, len(sim.records)), ("committed", 1))
        self.assertLessEqual(e.resolutions[0][0], 60)

    def test_lookup_absent_then_attempts_again(self):
        e, sim, _ = self.run_one("airline-rebook-b", {1: "lost"})
        self.assertEqual((e.state, e.attempts, len(sim.records)),
                         ("committed", 2, 1))

    def test_none_contract_escalates_not_retries(self):
        e, sim, _ = self.run_one("hotel-cancel-direct", {1: "late"},
                                 stock=2)
        self.assertEqual((e.state, len(sim.records)), ("escalated", 1))

    def test_message_is_at_most_once(self):
        e, sim, _ = self.run_one("customer-sms", {1: "late"})
        self.assertEqual((e.state, sim.calls), ("abandoned", 1))

    def test_committed_key_is_not_called_again(self):
        e, sim, ex = self.run_one("processor-refund")
        ex.run(KeyIssuer().mint(P, "processor-refund", REQ), REQ)
        self.assertEqual(sim.calls, 1)

    def test_expired_key_is_not_replayed(self):
        sim = SupplierSim(spec("processor-refund"), faults={1: "late"})
        ek = KeyIssuer().mint(P, "processor-refund", REQ, at=0.0)
        ex = Executor(Ledger(), {"processor-refund": sim})
        ex.now = 25 * 3600.0
        e = ex.run(ek, REQ)
        self.assertEqual((e.state, sim.calls), ("escalated", 1))


class ReplayTest(unittest.TestCase):
    def test_keyed_replay_has_no_duplicates(self):
        r = replay.run(2_000, 0.05, keyed=True)
        self.assertEqual(r.keyed_effects, 2_000)
        self.assertEqual(r.report.duplicates, 0)
        self.assertLessEqual(r.max_resolve_s, 60)

    def test_unkeyed_replay_duplicates(self):
        r = replay.run(2_000, 0.05, keyed=False)
        self.assertGreater(r.report.duplicates, 0)

    def test_no_key_injection_fails_the_checker(self):
        r = replay.run(2_000, 0.05, keyed=True, inject="no-key")
        self.assertFalse(r.report.ok)


class SagaTest(unittest.TestCase):
    def test_safe_order_strands_nobody(self):
        self.assertEqual(saga.inject(300, saga.SAFE)["stranded"], 0)

    def test_pilot_order_strands(self):
        self.assertGreater(saga.inject(300, saga.PILOT)["stranded"], 0)

    def test_break_compensates_in_reverse(self):
        s = saga.run_saga(saga.SAFE, "issue", "refused")
        self.assertEqual(s.compensated,
                         ["processor-refund", "airline-release-hold"])
        self.assertTrue(s.old_seat)


if __name__ == "__main__":
    unittest.main()
