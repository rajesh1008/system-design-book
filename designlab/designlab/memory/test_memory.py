"""Tests for the governed memory store (Chapter 22). Offline."""
from __future__ import annotations

import unittest

from chain.record import Proposal
from common.trail import check_trail
from isolation.blast import OutOfScope
from planes import ContextPacket, Fact

from memory import (Draft, OlderThanHead, Source,
                    StaleHead, WriteRefused, audit_legacy, authorize,
                    forget, naive_forget, restore)
from memory.demo import (LATER, LUCIA, START, TOKYO, TURN, _control,
                         _family, new_store, tok)
from memory.forget import remaining, snapshot
from memory.render import to_items

CONF = Source("CON-7731402", "customer-confirmed", "Window from now on.")


class WriteGate(unittest.TestCase):
    def test_refuses_without_provenance_scope_confidence(self):
        s = new_store()
        with self.assertRaises(WriteRefused) as e:
            s.write(tok(TOKYO), Draft("seat", "aisle", None, None, None))
        self.assertEqual(e.exception.missing,
                         ["provenance: source event", "scope", "confidence"])
        self.assertEqual(s.records, {})
        self.assertIn("memory.refused", s.trail.lines[-1])

    def test_standing_needs_confirmation(self):
        with self.assertRaises(WriteRefused):
            new_store().write(tok(TOKYO),
                              Draft("seat", "aisle", "standing", TURN, 0.9))

    def test_trip_scope_needs_itinerary(self):
        with self.assertRaises(WriteRefused):
            new_store().write(tok(TOKYO),
                              Draft("seat", "aisle", "trip", TURN, 0.9))

    def test_high_consequence_never_inferred(self):
        d = Draft("refund", "credit", "trip",
                  Source("CON-1", "agent-inferred"), 0.9, trip=TOKYO)
        with self.assertRaises(WriteRefused):
            new_store().write(tok(TOKYO), d)

    def test_trip_outside_token_is_out_of_scope(self):
        d = Draft("seat", "aisle", "trip", TURN, 0.9, trip=LATER[0])
        with self.assertRaises(OutOfScope):
            new_store().write(tok(TOKYO), d)

    def test_every_written_memory_has_provenance_and_scope(self):
        s = new_store()
        s.write(tok(TOKYO), Draft("seat", "aisle", "trip", TURN, 0.9,
                                  trip=TOKYO))
        s.write(tok(TOKYO), Draft("seat", "window", "standing", CONF, 0.9))
        for r in s.records.values():
            self.assertTrue(r.source.event_id and r.scope and r.confidence)
        self.assertEqual(check_trail(s.trail.lines), [])


class OneOff(unittest.TestCase):
    def test_trip_memory_not_read_on_other_trips(self):
        s = new_store()
        s.write(tok(TOKYO), Draft("seat", "aisle", "trip", TURN, 0.9,
                                  trip=TOKYO,
                                  observed_at="2026-02-09T18:40:00-06:00"))
        for it in LATER:
            self.assertEqual(s.read(tok(it)), [])


class Supersession(unittest.TestCase):
    def setUp(self):
        self.s = new_store()
        self.t = tok(LATER[2])
        self.v1 = self.s.write(self.t, Draft(
            "seat", "window", "standing", CONF, 0.95,
            observed_at="2026-05-04T10:12:00-05:00"))

    def test_stale_head_refused(self):
        with self.assertRaises(StaleHead):
            self.s.write(self.t, Draft("seat", "aisle", "standing", CONF,
                                       0.9), expected_head=None)

    def test_older_observation_refused(self):
        with self.assertRaises(OlderThanHead):
            self.s.write(self.t, Draft(
                "seat", "aisle", "standing", CONF, 0.9,
                observed_at="2026-02-09T18:40:00-06:00"),
                expected_head=self.v1.memory_id)

    def test_new_version_supersedes_and_history_kept(self):
        v2 = self.s.write(self.t, Draft(
            "seat", "window, ahead of the wing", "standing", CONF, 0.95,
            observed_at="2026-05-06T15:03:00-05:00"),
            expected_head=self.v1.memory_id)
        self.assertEqual(v2.supersedes, self.v1.memory_id)
        self.assertEqual(v2.version, 2)
        self.assertEqual([r.value for r in self.s.read(self.t)],
                         ["window, ahead of the wing"])
        hist = self.s.history(tok(LATER[2], role="agent-desk"), "seat")
        self.assertEqual([r.status for r in hist], ["superseded", "active"])
        self.assertEqual(self.s.history(self.t, "seat"), [])


class Scope(unittest.TestCase):
    def setUp(self):
        self.s = new_store()
        t = tok(LATER[2])
        self.s.write(t, Draft("seat", "window", "standing", CONF, 0.9))
        self.s.write(t, Draft("health", "knee", "standing",
                              Source("CON-2", "desk-entered"), 0.9))

    def test_cross_tenant_read_denied_and_logged(self):
        with self.assertRaises(OutOfScope):
            self.s.read(tok(LATER[2]), tenant="CUS-020771")
        self.assertIn("memory.read_denied", self.s.trail.lines[-1])

    def test_other_tenant_sees_nothing(self):
        self.assertEqual(self.s.read(tok(LATER[2], tenant="CUS-020771")), [])

    def test_roles(self):
        def n(role):
            return len(self.s.read(tok(LATER[2], role=role)))
        self.assertEqual((n("agent-loop"), n("agent-desk"), n("analytics")),
                         (1, 2, 0))

    def test_session_memory_ends_with_session(self):
        t = tok(LATER[2])
        self.s.write(t, Draft("meal", "none", "session", TURN, 0.9))
        self.assertEqual(len(self.s.read(tok(LATER[2], n=2))), 1)
        self.assertEqual(self.s.close_session(t), 1)


class Authority(unittest.TestCase):
    packet = ContextPacket(LATER[2], {
        "voucher_promise": Fact("voucher_promise", 75.0,
                                "memory:MR-00007", START),
        "contact_record": Fact("contact_record", "CON-7730988",
                               "crm-contacts", START)})
    p = Proposal("voucher", LATER[2], 75.0, "remembered promise")

    def test_memory_ground_escalates(self):
        c = _control()
        d = authorize(c, self.p, self.packet, ["memory:MR-00007"])
        self.assertEqual(d.verdict, "escalate")
        self.assertIsNone(d.permission)
        self.assertIn(d.pending_id, c.pending)

    def test_fact_sourced_from_memory_escalates(self):
        d = authorize(_control(), self.p, self.packet,
                      ["fact:voucher_promise"])
        self.assertEqual(d.verdict, "escalate")

    def test_record_ground_permits(self):
        d = authorize(_control(), self.p, self.packet,
                      ["fact:contact_record"])
        self.assertEqual(d.verdict, "permit")


class Forgetting(unittest.TestCase):
    def test_naive_misses_derived(self):
        s = new_store()
        _family(s)
        naive_forget(s, LUCIA)
        self.assertEqual(len(remaining(s, LUCIA)), 2)

    def test_forget_propagates_and_tombstones(self):
        s = new_store()
        _family(s)
        gone = forget(s, LUCIA)
        self.assertEqual(len(gone), 6)
        self.assertEqual(remaining(s, LUCIA), [])
        self.assertTrue(all(s.records[i].value == "" for i in gone))
        self.assertEqual(len(s.tombstones), 6)

    def test_restore_replays_tombstones(self):
        s = new_store()
        _family(s)
        snap = snapshot(s)
        forget(s, LUCIA)
        self.assertEqual(restore(s, snap, replay=True), [])
        self.assertEqual(s.read(tok(LATER[2])), [])

    def test_restore_without_replay_resurrects(self):
        s = new_store()
        _family(s)
        snap = snapshot(s)
        forget(s, LUCIA)
        self.assertEqual(len(restore(s, snap, replay=False)), 6)


class Legacy(unittest.TestCase):
    def test_audit_counts(self):
        from corpus.generate import generate
        a = audit_legacy(generate()["memories"])
        self.assertEqual(a["notes"], sum(a["outcomes"].values()))
        self.assertEqual(a["with_scope"], 0)
        self.assertGreater(a["outcomes"]["no source"], 0)


class Packing(unittest.TestCase):
    def test_whole_records_under_cap(self):
        s = new_store()
        t = tok(LATER[2])
        for k in range(30):
            s.write(t, Draft(f"pref-{k}", "x" * 80, "standing",
                             Source(f"CON-{k}", "customer-confirmed"), 0.9))
        s.write(t, Draft("seat", "window", "standing", CONF, 0.9))
        items, left = to_items(s.read(t), cap=300)
        self.assertLessEqual(sum(i.tokens for i in items), 300)
        self.assertEqual(items[0].text.split()[3], "seat:")
        self.assertTrue(all("evidence only" in i.text for i in items))
        self.assertEqual(len(items) + len(left), 31)


if __name__ == "__main__":
    unittest.main()
