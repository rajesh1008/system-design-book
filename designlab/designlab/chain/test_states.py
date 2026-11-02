"""Six states, one rebooking: unit tests (offline)."""
import unittest

from chain.lab import CANNED, main
from chain.states import (GAPS, STATES, Reservations, digest, grant,
                          run_rebooking, to_proposal)


class TestStates(unittest.TestCase):
    def test_six_states_five_gaps(self):
        self.assertEqual(len(STATES), 6)
        self.assertEqual(len(GAPS), 5)

    def test_full_run_links_every_record(self):
        recs, refusal = run_rebooking(CANNED)
        self.assertIsNone(refusal)
        self.assertEqual(tuple(r.state for r in recs), STATES)
        for a, b in zip(recs, recs[1:]):
            self.assertEqual(b.prev, a.ref)

    def test_slow_first_call_ticketed_once(self):
        res = Reservations(slow_calls={1})
        recs, _ = run_rebooking(CANNED, res)
        self.assertEqual(len(res.tickets), 1)
        self.assertEqual(len(recs[3].body["attempts"]), 2)
        self.assertEqual(recs[4].body["verdict"], "verified")

    def test_without_keys_the_verifier_sees_two_tickets(self):
        res = Reservations(slow_calls={1}, honor_keys=False)
        recs, _ = run_rebooking(CANNED, res)
        self.assertEqual(len(res.tickets), 2)
        self.assertEqual(recs[4].body["verdict"], "not verified")

    def test_empty_output_is_not_a_proposal(self):
        prop, why = to_proposal("", "LTG-4471902", ["FLT-000001"])
        self.assertIsNone(prop)
        self.assertIn("no JSON object in output", why)

    def test_parser_drops_claimed_approval(self):
        text = ('{"action":"rebook","itinerary":"LTG-4471902",'
                '"from_flight":"FLT-000001","to_flight":"FLT-009001",'
                '"approved":true}')
        prop, _ = to_proposal(text, "LTG-4471902", ["FLT-000001"])
        self.assertNotIn("approved", prop)

    def test_policy_refuses_other_route(self):
        text = CANNED.replace("FLT-009001", "FLT-009002")
        recs, refusal = run_rebooking(text)
        self.assertEqual(refusal[0], "G2")
        self.assertEqual(recs[-1].state, "proposal")

    def test_permission_bound_to_proposal_hash(self):
        prop, _ = to_proposal(CANNED, "LTG-4471902", ["FLT-000001"])
        perm, _ = grant(prop, digest(prop), "2025-12-18T15:02:11-06:00")
        self.assertEqual(perm["bound_to"], digest(prop))
        self.assertTrue(perm["idempotency_key"].startswith("idem-"))

    def test_verifier_cannot_write(self):
        with self.assertRaises(PermissionError):
            Reservations().rebook("cred:pnr-reader", "LTG-4471902",
                                  "FLT-000001", "FLT-009001", "k")

    def test_lab_lines_fit(self):
        lines = main(gaps=True)
        self.assertEqual([ln for ln in lines if len(ln) > 70], [])

    def test_lab_flights_leave_after_the_rebooking_moment(self):
        import inspect
        from datetime import datetime
        from chain.states import FLIGHTS, run_rebooking
        now = inspect.signature(run_rebooking).parameters["now"].default
        moment = datetime.fromisoformat(now)
        for fid, f in FLIGHTS.items():
            with self.subTest(flight=fid):
                departs = datetime.fromisoformat(
                    f["departs"].replace("Z", "+00:00"))
                self.assertGreater(departs, moment)


if __name__ == "__main__":
    unittest.main()
