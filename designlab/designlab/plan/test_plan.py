"""Chapter 48 tests: the card, the four questions, the renaming cycle,
the runtimes table, mandates down a hire chain, and the plan linter."""
import copy
import unittest

from plan import core, template
from plan.demo import _plan


class Card(unittest.TestCase):
    def test_split_and_annual(self):
        c = core.card()
        self.assertEqual(c["split"], {"agent": 44, "assisted": 24,
                                      "self_service": 23, "person": 9})
        self.assertEqual(c["split_total"], 100)
        self.assertEqual(c["annual_check_m"], 20.5)

    def test_year_end_values(self):
        rows = {r["key"]: r["year_end"] for r in core.card()["row"]}
        self.assertEqual(rows["cost_agent"], "$1.61")
        self.assertEqual(rows["verified"], "99.5%")
        self.assertEqual(rows["duplicates"], "212")
        self.assertEqual(rows["incidents"], "7")
        self.assertEqual(rows["p95"], "38 s")
        self.assertEqual(rows["refund_error"], "0.3%")


class Chain(unittest.TestCase):
    def test_four_links_named(self):
        for d in ("lakeshore-rebooking", "lakeshore-refunds"):
            f = core.four(d)
            for k in core.LINKS:
                self.assertTrue(f[k], (d, k))


class Renames(unittest.TestCase):
    def test_only_the_chain_answers_all_four(self):
        full = [r.name for r in core.renames() if not r.missing]
        self.assertEqual(full, ["Lakeshore chain"])

    def test_every_name_misses_verification(self):
        for r in core.renames():
            if r.name != "Lakeshore chain":
                self.assertIn("verification", r.missing, r.name)


class Runtimes(unittest.TestCase):
    def test_outcome_check_never_moves(self):
        rows = {r["name"]: r for r in core.runtimes()}
        self.assertEqual(rows["outcome check"]["state"], "never")
        self.assertEqual(sum(r["state"].startswith("absorbed")
                             for r in rows.values()), 7)


class Hire(unittest.TestCase):
    def test_shipped_chain_narrows(self):
        self.assertEqual(core.hire(), [])

    def test_widened_mandate_fails(self):
        hops = copy.deepcopy(core.load("hire.toml")["hop"])
        hops[1]["mandate"]["expires_min"] = 90
        self.assertTrue(any("longer" in f for f in core.hire(hops)))


class Plan(unittest.TestCase):
    def test_shipped_plan_is_clean(self):
        self.assertEqual(template.check(core.load("lakeshore-y2.toml")),
                         [])

    def test_each_fault_fails_its_rule(self):
        want = {"roadmap": "PLN-3", "retired": "PLN-9",
                "undated": "PLN-5", "self-signed": "PLN-1",
                "crowded": "PLN-8"}
        for fault, rule in want.items():
            found = template.check(_plan(fault))
            self.assertTrue(any(f.startswith(rule) for f in found),
                            (fault, found))

    def test_pins_inside_window(self):
        rows = template.window(core.load("lakeshore-y2.toml"))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(days > 300 for _, _, days in rows))


if __name__ == "__main__":
    unittest.main()
