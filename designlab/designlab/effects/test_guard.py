"""Tests for effects.guard: the tool refuses unkeyed, unledgered,
unregistered, and wrongly credentialed calls."""
from __future__ import annotations

import unittest

from chain.record import Permission
from corpus.tools import TOOLS, SupplierSim, ToolSpec, NATIVE
from effects import Executor, KeyIssuer, Ledger
from effects.guard import (GATEWAY, Credential, GuardedClient, Refused,
                           writers_outside_gateway)

REFUND = next(t for t in TOOLS if t.name == "processor-refund")
REQ = {"target": "CHG-1", "amount_usd": 120.0}
PERM = Permission("PRM-1", "approver-desk", "refunds-v3", 1500.0)


def setup(credential=GATEWAY):
    ledger = Ledger()
    sim = SupplierSim(REFUND)
    return ledger, sim, GuardedClient(sim, ledger, credential)


class TestGuard(unittest.TestCase):
    def test_unkeyed_call_refused_before_supplier(self):
        _, sim, g = setup()
        with self.assertRaises(Refused):
            g.call(REQ)
        self.assertEqual(sim.calls, 0)
        self.assertEqual(sim.records, [])

    def test_key_without_ledger_entry_refused(self):
        _, sim, g = setup()
        with self.assertRaises(Refused):
            g.call(REQ, key="idem-own", ref="idem-own")
        self.assertEqual(sim.records, [])

    def test_other_credential_refused(self):
        _, sim, g = setup("int-fin-02")
        with self.assertRaises(Refused):
            g.call(REQ, key="k", ref="k")
        self.assertEqual(g.refusals[0][1],
                         "credential int-fin-02 may not write")

    def test_unregistered_tool_refused(self):
        ledger = Ledger()
        spec = ToolSpec("side-refund", "payment", "refund", NATIVE,
                        "none", 0)
        g = GuardedClient(SupplierSim(spec), ledger)
        with self.assertRaises(Refused):
            g.call(REQ, key="k", ref="k")

    def test_executor_runs_through_guard(self):
        ledger, sim, g = setup()
        ek = KeyIssuer().mint(PERM, "processor-refund", REQ)
        e = Executor(ledger, {"processor-refund": g}).run(ek, REQ)
        self.assertEqual(e.state, "committed")
        self.assertEqual(len(sim.records), 1)
        self.assertEqual(g.refusals, [])

    def test_late_answer_still_one_effect(self):
        ledger, sim, g = setup()
        faults = iter(["late", ""])
        ex = Executor(ledger, {"processor-refund": g},
                      faults=lambda tool: next(faults, ""))
        ek = KeyIssuer().mint(PERM, "processor-refund", REQ)
        self.assertEqual(ex.run(ek, REQ).state, "committed")
        self.assertEqual(len(sim.records), 1)

    def test_committed_entry_refuses_a_second_call(self):
        ledger, sim, g = setup()
        ek = KeyIssuer().mint(PERM, "processor-refund", REQ)
        Executor(ledger, {"processor-refund": g}).run(ek, REQ)
        with self.assertRaises(Refused):
            g.call(REQ, key=ek.key, ref=ek.key)
        self.assertEqual(len(sim.records), 1)

    def test_inventory(self):
        creds = [Credential(GATEWAY, "gateway", ("processor",)),
                 Credential("int-fin-02", "payments-ops", ("processor",)),
                 Credential("ro-reports", "finance", ())]
        out = [c.name for c in writers_outside_gateway(creds)]
        self.assertEqual(out, ["int-fin-02"])


if __name__ == "__main__":
    unittest.main()
