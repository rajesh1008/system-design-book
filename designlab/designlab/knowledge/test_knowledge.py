"""Offline tests for the Chapter 20 knowledge plane."""
import os
import unittest
from datetime import date

os.environ.setdefault("DESIGNLAB_OFFLINE", "1")

from . import entitle as E
from . import graph as G
from . import layer as L
from . import replay as R
from . import sql as S
from .questions import CALLERS
from .translate import CONTRACT

TLA = E.from_token(CALLERS["talvarez"])
PNA = E.from_token(CALLERS["pnatarajan"])


class TestLayer(unittest.TestCase):
    def setUp(self):
        self.layer = L.load()

    def test_forty_one_metrics_each_owned(self):
        self.assertEqual(len(self.layer.metrics), 41)
        for m in self.layer.metrics.values():
            self.assertTrue(m.owner, m.name)

    def test_contract_enum_is_the_layer(self):
        enum = next(f for f in CONTRACT.fields if f.name == "metric").values
        self.assertEqual(set(enum), set(self.layer.metrics) | {"none"})

    def test_unknown_value_refused_not_zero(self):
        q = L.MetricQuery("refund_avg_usd", date(2025, 1, 1),
                          date(2025, 12, 31),
                          filters=(("change_type", "involuntary"),))
        p = L.problems(self.layer, q)
        self.assertTrue(p and "involuntary_refund" in p[0])


class TestGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = S.Guard()

    def ask(self, *a, ent=TLA, **k):
        return self.g.ask(L.MetricQuery(*a, **k), ent)

    def test_answered_with_estimate(self):
        d = self.ask("refunds_count", date(2025, 1, 1), date(2025, 12, 31))
        self.assertEqual(d.status, "answered")
        self.assertIsNotNone(d.estimate)
        self.assertEqual(d.rows[0][-2], 704_000)

    def test_reasons(self):
        cases = [
            (("refund_margin_usd", date(2025, 1, 1), date(2025, 12, 31)),
             {}, "not_in_layer"),
            (("status_polls", date(2026, 1, 1), date(2026, 5, 26)),
             {"grain": "day"}, "window"),
            (("status_polls", date(2026, 4, 27), date(2026, 5, 26)),
             {"dims": ("carrier",)}, "cost"),
            (("refunds_amount_usd", date(2026, 1, 1), date(2026, 3, 31)),
             {"dims": ("carrier",)}, "entitlement"),
        ]
        for args, kw, want in cases:
            with self.subTest(want=want):
                self.assertEqual(self.ask(*args, **kw).reason, want)

    def test_write_refused(self):
        d = S.Guard(raw_allowed=True).ask_sql(
            "DELETE FROM refunds WHERE 1=1", TLA)
        self.assertEqual(d.reason, "write")

    def test_no_estimate_no_query(self):
        g = S.Guard(estimator=lambda reads, months: None)
        d = g.ask(L.MetricQuery("refunds_count", date(2025, 1, 1),
                                date(2025, 12, 31)), TLA)
        self.assertEqual((d.status, d.reason), ("refused", "unestimated"))
        self.assertEqual(d.rows, [])

    def test_row_limit_truncates(self):
        d = self.ask("changes_count", date(2025, 1, 1), date(2025, 12, 31),
                     dims=("desk", "carrier"), grain="day", limit=100_000)
        self.assertEqual(len(d.rows), 1000)
        self.assertTrue(d.truncated)

    def test_trail_names_the_grant(self):
        d = self.ask("refunds_count", date(2025, 1, 1), date(2025, 12, 31))
        self.assertIn('"grant": "sess-0527-tla"', d.trail_line)


class TestEntitlement(unittest.TestCase):
    def test_forged_token(self):
        body, sig = CALLERS["talvarez"].rsplit(".", 1)
        forged = E.issue("talvarez", ["finance"], [], "sess-0527-tla")
        with self.assertRaises(E.BadToken):
            E.from_token(forged.rsplit(".", 1)[0] + "." + sig)

    def test_finance_answers_ops_refused(self):
        g = S.Guard()
        q = L.MetricQuery("refunds_amount_usd", date(2026, 1, 1),
                          date(2026, 3, 31), ("carrier",))
        self.assertEqual(g.ask(q, PNA).status, "answered")
        self.assertEqual(g.ask(q, TLA).reason, "entitlement")

    def test_desk_scope_applied(self):
        d = S.Guard().ask(L.MetricQuery(
            "approval_wait_p95_minutes", date(2026, 5, 1),
            date(2026, 5, 26), ("desk",)), TLA)
        self.assertEqual({r[1] for r in d.rows}, {"CHI-2", "CHI-3"})


class TestReplay(unittest.TestCase):
    def test_card_numbers(self):
        rep = R.run()
        self.assertEqual(len(rep.rows), 1436)
        self.assertEqual(rep.estimated, R.compiled_count(rep))
        self.assertEqual(rep.by_reason["cost"], 42)
        self.assertEqual(rep.audit_findings, [])


class TestGraph(unittest.TestCase):
    def test_authority_not_transitive(self):
        g = G.lakeshore_sample()
        self.assertTrue(G.may_act(g, "Ngozi Okafor", "LTG-5208841")[0])
        self.assertFalse(G.may_act(g, "Ngozi Okafor", "LTG-5208842")[0])

    def test_fanout_cap_reports_incomplete(self):
        g = G.lakeshore_sample()
        w = G.traverse(g, "FLT-904417", [("on_flight", "in"),
                                         ("has_segment", "in")],
                       "itinerary", fanout_cap=50)
        self.assertFalse(w.complete)
        self.assertIn("fan-out cap", w.stopped_by)


class TestLiveReplay(unittest.TestCase):
    def test_recorded_questions(self):
        from .live import run
        lines, rows = run(replay=True)
        by = {r["id"]: r for r in rows}
        self.assertEqual(by["Q1"]["layer"], "answered")
        self.assertEqual(by["Q4"]["layer"], "clarify")
        self.assertEqual(by["Q6"]["raw"], "cost")
        self.assertEqual(by["Q10"]["layer"], "not_in_layer")
        self.assertEqual(by["Q12"]["layer"], "not_in_layer")


if __name__ == "__main__":
    unittest.main()
