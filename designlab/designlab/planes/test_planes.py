"""Chapter 6 tests: contracts, the path test, and the autonomy table.

Offline and seeded. Each contract in contracts.toml names one test here.
"""
import copy
import unittest

from chain.record import ChainRecord, Permission, Proposal, Refused
from common.clock import FixedClock

from planes.action import CUSTOMER_STATES, customer_state
from planes.autonomy import (LEVELS, ceiling, check_autonomy,
                             load_autonomy)
from planes.contracts import check_contracts, load_contracts
from planes.knowledge import Fact, KnowledgePlane, NotFound
from planes.lab import START, build, cases, replay
from planes.paths import probe_tools, unmediated_paths, wiring

SEED = 6


def small(n=40):
    return cases(SEED, n)


class Contracts(unittest.TestCase):
    def test_every_contract_names_an_existing_test(self):
        self.assertEqual(check_contracts(load_contracts()), [])

    def test_c1_context_flags_stale_and_refuses_unknown(self):
        k = KnowledgePlane({"LTG-1": [
            Fact("fare_rules", "x", "airline-fares",
                 "2026-01-12T13:59:30+00:00"),
            Fact("payment_card", "y", "payment-profile",
                 "2026-01-12T12:00:00+00:00")]},
            FixedClock(START, 0))
        ctx = k.context("LTG-1")
        self.assertEqual(ctx.stale, ["payment_card"])
        for f in ctx.facts.values():
            self.assertTrue(f.source and f.as_of)
        with self.assertRaises(NotFound):
            k.context("LTG-404")

    def test_c2_every_proposal_gets_one_decision(self):
        batch = small()
        s = build(batch)
        out = replay(s, batch)
        verdicts = {o.verdict for o in out["outcomes"]}
        self.assertTrue(verdicts <= {"permit", "escalate", "deny"})
        # One decision line per proposal, plus one per approval.
        approvals = sum(1 for o in out["outcomes"] if o.handoff == "sync")
        self.assertEqual(out["decisions"], len(batch) + approvals)

    def test_c3_gateway_refuses_foreign_or_altered_permission(self):
        batch = small(5)
        s = build(batch)
        p = Proposal("voucher", batch[0]["itinerary"], 50.0, "delay")
        forged = ChainRecord(proposal=p, permission=Permission(
            "PRM-99999", "policy-engine", "vouchers-v1", 100.0),
            idempotency_key="k")
        with self.assertRaises(Refused):
            s.gateway.call("voucher", forged)
        d = s.control.decide(p, s.knowledge.context(p.itinerary))
        self.assertEqual(d.verdict, "permit")
        bigger = Proposal("voucher", p.itinerary, 100.0, "delay")
        swapped = ChainRecord(proposal=bigger, permission=d.permission,
                              idempotency_key=d.key)
        with self.assertRaises(Refused) as e:
            s.gateway.call("voucher", swapped)
        self.assertIn("permission is for another proposal", e.exception.missing)
        self.assertEqual(s.world.effects, [])

    def test_c4_every_effect_has_a_trail_line(self):
        batch = small()
        s = build(batch)
        replay(s, batch)
        refs = {e["id"] for e in s.world.effects}
        lines = [ln for ln in s.trail.writer.lines if '"effect"' in ln]
        self.assertTrue(refs)
        for ref in refs:
            self.assertTrue(any(f'"{ref}"' in ln for ln in lines), ref)

    def test_c5_every_decision_is_written(self):
        batch = small()
        s = build(batch)
        out = replay(s, batch)
        escalated = sum(1 for o in out["outcomes"]
                        if o.verdict == "escalate")
        lines = [ln for ln in s.trail.writer.lines
                 if '"verdict": "escalate"' in ln]
        self.assertGreaterEqual(len(lines), escalated)
        self.assertTrue(s.trail.intact())

    def test_c6_done_only_when_verified_by_non_actor(self):
        batch = cases(SEED)
        s = build(batch)
        out = replay(s, batch)
        self.assertEqual(out["told_done_unverified"], 0)
        lost = [c["itinerary"] for c in batch if c["lost"]]
        told = {o.itinerary: o.customer for o in out["outcomes"]}
        for itin in lost:
            self.assertNotEqual(told[itin], "done")

    def test_customer_state_never_done_on_actor_says_so(self):
        p = Proposal("rebook", "LTG-1", 10.0, "r")
        r = ChainRecord(proposal=p, execution={"id": "PNR-1"},
                        verification={"verified_by": "agent-loop",
                                      "ok": True})

        class D:
            verdict, reason = "permit", ""
        self.assertEqual(customer_state(D, r), "in progress")


class PathTest(unittest.TestCase):
    def test_clean_wiring_has_no_unmediated_path(self):
        s = build(small(5))
        self.assertEqual(unmediated_paths(wiring(s.loop)), [])
        self.assertEqual(probe_tools(s.loop, s.world), [])

    def test_injected_fast_path_is_found_both_ways(self):
        s = build(small(5), bypass=True)
        found = unmediated_paths(wiring(s.loop))
        self.assertEqual(found, [["agent-loop", "tool:refund_fast",
                                  "processor"]])
        self.assertEqual(probe_tools(s.loop, s.world), ["refund_fast"])

    def test_undeclared_tool_shows_as_unknown_system(self):
        s = build(small(5))

        class Helper:          # holds a client, declares no system
            def __init__(self, world):
                self.world = world

            def __call__(self, record):
                return self.world.voucher("LTG-1", 25.0)
        s.loop.tools["goodwill_helper"] = Helper(s.world)
        static = unmediated_paths(wiring(s.loop))
        self.assertEqual(static, [["agent-loop", "tool:goodwill_helper",
                                   "unknown-system"]])
        self.assertIn("goodwill_helper", probe_tools(s.loop, s.world))

    def test_bypass_effects_carry_no_permission(self):
        batch = cases(SEED)
        s = build(batch, bypass=True)
        out = replay(s, batch)
        self.assertGreater(out["unmediated"], 0)
        for e in s.world.unmediated():
            self.assertIsNone(e["key"])

    def test_policy_inside_the_loop_is_refused(self):
        batch = [c for c in cases(SEED) if c["task"] == "refund"][:1]
        s = build(batch, policy_in_loop=True)
        o = s.loop.run(batch[0], None)
        self.assertIn("permission from outside the loop", o.verdict)
        self.assertEqual(s.world.effects, [])


class Autonomy(unittest.TestCase):
    def test_table_is_within_every_ceiling(self):
        self.assertEqual(check_autonomy(load_autonomy()), [])

    def test_ceiling_rule(self):
        self.assertEqual(ceiling(2, 2, 0), "suggest")
        self.assertEqual(ceiling(0, 2, 2), "act_with_approval")
        self.assertEqual(ceiling(2, 0, 2), "act_with_approval")
        self.assertEqual(ceiling(1, 1, 2), "act_and_notify")
        self.assertEqual(ceiling(2, 2, 2), "act_unattended")

    def test_no_task_type_runs_above_its_ceiling(self):
        t = load_autonomy()
        for r in t.rows.values():
            self.assertLessEqual(LEVELS.index(r.level),
                                 LEVELS.index(r.ceiling), r.task)

    def test_raising_refunds_fails(self):
        t = load_autonomy()
        t.rows["refund"].level = "act_and_notify"
        self.assertEqual(check_autonomy(t),
                         ["refund: act_and_notify above ceiling "
                          "act_with_approval"])

    def test_signed_override_with_expiry_is_accepted(self):
        t = load_autonomy()
        r = copy.deepcopy(t.rows["refund"])
        r.task, r.level = "involuntary_refund_storm", "act_and_notify"
        r.limit_usd = 500.0
        r.override = {"signed_by": "Head of Risk and Compliance"}
        t.rows[r.task] = r
        self.assertEqual(len(check_autonomy(t)), 1)
        r.override["expires"] = "2026-09-11T05:00:00+00:00"
        self.assertEqual(check_autonomy(t), [])

    def test_unattended_needs_limit_budget_and_audit(self):
        t = load_autonomy()
        t.rows["voucher"].daily_budget_usd = None
        t.rows["voucher"].audit_sample = None
        self.assertEqual(len(check_autonomy(t)), 2)

    def test_customer_states_come_from_the_chain(self):
        t = load_autonomy()
        for r in t.rows.values():
            self.assertTrue(set(r.customer_sees) <= set(CUSTOMER_STATES))
        t.rows["rebook"].customer_sees = ["confirmed"]
        self.assertEqual(len(check_autonomy(t)), 1)

    def test_unattended_tasks_are_counted_as_agent_only_when_verified(self):
        batch = cases(SEED)
        out = replay(build(batch), batch)
        for o in out["outcomes"]:
            if o.path == "agent":
                self.assertEqual(o.customer, "done")

    def test_daily_budget_escalates_vouchers(self):
        t = load_autonomy()
        t.rows["voucher"].daily_budget_usd = 200.0
        batch = [c for c in cases(SEED) if c["task"] == "voucher"
                 and c["usd"] <= 100][:6]
        s = build(batch, table=t)
        out = replay(s, batch)
        self.assertLessEqual(s.control.spent_usd.get("voucher", 0), 200.0)
        self.assertTrue(any(o.verdict == "escalate"
                            for o in out["outcomes"]))


if __name__ == "__main__":
    unittest.main()
