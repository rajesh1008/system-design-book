import unittest

from corpus.tools import (KeyConflict, LOOKUP, NATIVE, NONE, TOOLS,
                          SupplierSim, SupplierTimeout, counts, spec)


class ToolsTest(unittest.TestCase):
    def test_eighteen_tools_three_contracts(self):
        self.assertEqual(len(TOOLS), 18)
        self.assertEqual(len({t.name for t in TOOLS}), 18)
        c = counts()
        total = {s: sum(row[s] for row in c.values())
                 for s in (NATIVE, LOOKUP, NONE)}
        self.assertEqual(total, {NATIVE: 7, LOOKUP: 7, NONE: 4})

    def test_native_key_replays_receipt(self):
        sim = SupplierSim(spec("processor-refund"), faults={1: "late"})
        req = {"intent": "I1", "target": "LTG-1", "amount_usd": 10.0}
        with self.assertRaises(SupplierTimeout):
            sim.call(req, key="k1")
        out = sim.call(req, key="k1")
        self.assertTrue(out["replayed"])
        self.assertEqual(len(sim.records), 1)

    def test_native_key_conflict(self):
        sim = SupplierSim(spec("processor-refund"))
        sim.call({"intent": "I1", "target": "T", "amount_usd": 1.0}, "k")
        with self.assertRaises(KeyConflict):
            sim.call({"intent": "I1", "target": "T", "amount_usd": 2.0},
                     "k")

    def test_none_contract_ignores_key(self):
        sim = SupplierSim(spec("hotel-cancel-direct"))
        sim.stock("H", 2)
        req = {"intent": "I1", "target": "H"}
        sim.call(req, key="k")
        sim.call(req, key="k")
        self.assertEqual([r["item"] for r in sim.records], [1, 2])

    def test_lookup_respects_visibility(self):
        sim = SupplierSim(spec("airline-rebook-b"))
        sim.call({"intent": "I", "target": "T"}, ref="r1", at=0.0,
                 lag=99.0)
        self.assertIsNone(sim.lookup("r1", 39.0))
        self.assertIsNotNone(sim.lookup("r1", 40.0))

    def test_lost_request_leaves_no_record(self):
        sim = SupplierSim(spec("car-cancel"), faults={1: "lost"})
        with self.assertRaises(SupplierTimeout):
            sim.call({"intent": "I", "target": "T"})
        self.assertEqual(sim.records, [])


if __name__ == "__main__":
    unittest.main()
