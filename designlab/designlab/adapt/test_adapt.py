"""Offline tests for the Chapter 17 adapt module. No model is called."""
import contextlib
import io
import unittest

from common.text import too_long

from . import cost as C
from . import evaluate as E
from . import lab as L
from . import prefs as P
from . import reward as R
from . import teacher as T
from .data import MONTHS, TYPES, UNCLEAR, by_month, generate, shorthand
from .learn import Student, tokens
from .tree import MARCUS, Request, walk

MSGS = generate(17)
RUN = L.run(17)


class TestData(unittest.TestCase):
    def test_same_seed_same_rows(self):
        self.assertEqual(generate(17)[:50], MSGS[:50])

    def test_golden_month_has_100_cases_a_type(self):
        may = E.first_messages(by_month(MSGS)["2026-05"])
        self.assertEqual(len(may), 1200)
        wanted = {}
        for m in may:
            wanted[m.wanted] = wanted.get(m.wanted, 0) + 1
        self.assertEqual(set(wanted.values()), {100})

    def test_chicago_offsets(self):
        dec = next(m for m in MSGS if m.month == "2025-12")
        may = next(m for m in MSGS if m.month == "2026-05")
        self.assertTrue(dec.at.endswith("-06:00"))
        self.assertTrue(may.at.endswith("-05:00"))

    def test_shorthand_only_from_april(self):
        early = [m for m in MSGS if m.month < "2026-04" and m.short]
        late = [m for m in MSGS if m.month >= "2026-04" and m.short]
        self.assertEqual(early, [])
        self.assertGreater(len(late), 100)
        self.assertEqual(shorthand("please cancel the flight"),
                         "pls cxl flt")

    def test_vague_messages_are_unclear(self):
        v = [m for m in MSGS if m.vague]
        self.assertTrue(v)
        self.assertTrue(all(m.label == UNCLEAR for m in v))

    def test_twelve_types(self):
        self.assertEqual(len(TYPES), 12)
        self.assertEqual(len(MONTHS), 6)


class TestLearn(unittest.TestCase):
    def test_tokens_have_bigrams(self):
        self.assertIn("cancel_hotel", tokens("Cancel hotel"))

    def test_student_learns_a_toy_split(self):
        s = Student.train(["refund my seat", "refund the bag",
                           "change my flight", "change the date"] * 5,
                          ["money", "money", "move", "move"] * 5)
        self.assertEqual(s.predict("refund please")[0], "money")
        self.assertEqual(s.predict("change it")[0], "move")


class TestEvaluate(unittest.TestCase):
    def test_time_split_has_no_overlap(self):
        o = E.overlap(RUN.train, RUN.test)
        self.assertEqual((o.same_case, o.same_text), (0, 0))
        self.assertEqual(E.gate(o), [])

    def test_random_split_fails_the_gate(self):
        tr, te, sc, o = L.leaky(17)
        self.assertGreater(o.same_case, 0)
        self.assertTrue(E.gate(o))
        self.assertGreater(sc.acc, 0.99)

    def test_paired_counts(self):
        m = RUN.test[:3]
        a = {x.msg_id: x.label for x in m}
        b = {x.msg_id: "nope" for x in m}
        self.assertEqual(E.paired(a, b, m), (3, 0))


class TestDistill(unittest.TestCase):
    def test_student_with_escalation_reaches_parity(self):
        ok, _ = E.parity(E.score(RUN.cas, RUN.test),
                         E.score(RUN.fr, RUN.test))
        self.assertTrue(ok)
        self.assertLess(RUN.escalated, 0.10)

    def test_student_alone_falls_short_on_new_words(self):
        ok, _ = E.parity(E.score(RUN.stu, RUN.test),
                         E.score(RUN.fr, RUN.test))
        self.assertFalse(ok)

    def test_threshold_tuned_on_a_quiet_month_fails(self):
        r = L.run(17, tau=None)
        ok, _ = E.parity(E.score(r.cas, r.test), E.score(r.fr, r.test))
        self.assertFalse(ok)
        self.assertLess(r.tau, L.FLOOR)

    def test_new_type_fails_parity(self):
        r = L.run(17, new_type=True)
        ok, why = E.parity(E.score(r.cas, r.test),
                           E.score(r.fr, r.test))
        self.assertFalse(ok)


class TestTeacher(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(T.parse("1 upgrade\n2. car_change\n", 3),
                         ["upgrade", "car_change", "unparsed"])

    def test_sim_teacher_is_close_to_reference(self):
        sim = T.sim_teacher(MSGS, 17)
        right = sum(sim[m.msg_id] == m.label for m in MSGS)
        self.assertGreater(right / len(MSGS), 0.98)

    def test_recorded_labels_replay_offline(self):
        from common.spend import SpendMeter
        sample = T.live_sample(MSGS, 100, 17)
        try:
            got, st = T.label(sample, "frontier", SpendMeter(),
                              offline=True)
        except LookupError:
            self.skipTest("no fixtures recorded")
        self.assertEqual(st["calls"], 10)
        self.assertEqual(sum(got[m.msg_id] == m.label for m in sample),
                         100)


class TestTreeAndCost(unittest.TestCase):
    def test_one_of_six_asks_is_distilled(self):
        out = [walk(r).outcome for r in MARCUS]
        self.assertEqual(out.count("adapt: distill"), 1)
        self.assertEqual(sum(o.startswith("adapt") for o in out), 1)

    def test_tree_stops_early(self):
        self.assertEqual(walk(Request("x")).outcome, "stop")
        self.assertEqual(walk(Request("x", "y", policy=True)).outcome,
                         "rule")
        self.assertEqual(walk(Request("x", "y")).outcome, "try context")

    def test_frontier_step_price(self):
        self.assertAlmostEqual(C.frontier_step(), 0.00504)

    def test_ratio_at_june_volume(self):
        s = C.distilled(RUN.escalated, C.GA_STEPS)
        self.assertGreater(s.ratio, 11)
        self.assertLess(C.distilled(RUN.escalated, C.PILOT_STEPS).ratio,
                        s.ratio)


class TestPrefs(unittest.TestCase):
    CARDS = P.cards(17)

    def test_effect_changes_are_dropped(self):
        pairs, dropped = P.export(self.CARDS)
        ids = {p.card_id for p in pairs}
        for c in self.CARDS:
            if c.amount_changed or c.kind_changed or c.rejected:
                self.assertNotIn(c.card_id, ids)
        self.assertGreater(dropped["effect changed"], 0)
        self.assertTrue(1500 < len(pairs) < 2100)

    def test_rule_fix(self):
        t = "The customer requested a refund because bag fee charged twice."
        self.assertEqual(P.rule_fix(t, "ANC"),
                         "ANC: bag fee charged twice; rule FR-207")

    def test_ranker_on_held_out_month(self):
        pairs, _ = P.export(self.CARDS)
        tr = [p for p in pairs if p.month < "2026-05"]
        te = [p for p in pairs if p.month == "2026-05"]
        rk = P.Ranker.train(tr)
        self.assertGreater(sum(map(rk.prefers, te)) / len(te), 0.9)

    def test_busy_desk_waves_more_through(self):
        shares = [s for _, _, s in P.wave_through(self.CARDS)]
        self.assertEqual(shares, sorted(shares))


class TestReward(unittest.TestCase):
    def test_each_grader_gets_what_it_pays_for(self):
        want = {R.naive: "claim", R.exists: "double", R.harness: "act"}
        for g, a in want.items():
            pol, _ = R.train(g)
            self.assertEqual(max(pol, key=pol.get), a)

    def test_only_the_harness_policy_succeeds(self):
        self.assertEqual(R.train(R.naive)[1], 0.0)
        self.assertGreater(R.train(R.harness)[1], 0.8)


class TestDemo(unittest.TestCase):
    def test_lines_fit_the_page(self):
        from .demo import main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main([])
            main(["--inject", "random"])
        self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
