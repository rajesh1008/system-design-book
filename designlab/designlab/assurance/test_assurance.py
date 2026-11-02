"""Chapter 36 tests: the hotel-note replay, the extended battery, the
golden-set gap, the destination bundle, the month trail and its
anchors, the evidence pack and tampering, admissibility, the finding,
the card, and the recorded live check."""
from __future__ import annotations

import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from common.redact import find_secrets
from common.text import too_long
from common.trail import check_trail
from evals import golden as G
from threats import battery as B
from threats import email

from . import admissible as A
from . import anchor, bundles, case, demo, findings, gaps, live, month
from . import pack as P
from . import scorecard

LINES = month.build().lines
HELD = anchor.anchors(LINES)
PACK = P.generate(LINES, HELD, "2026-06", demo.SEED)


def events(kind):
    return [json.loads(x) for x in LINES
            if json.loads(x)["event"] == kind]


class TestReplay(unittest.TestCase):
    def test_june_24_reaches_the_desk(self):
        r = case.replay(case.JUNE_24)
        self.assertEqual(r.reached, "desk")
        self.assertEqual(r.args["refund_to"], case.ATTACK_REF)

    def test_tokenizer_mints_a_valid_ref_from_the_note(self):
        _, minted = case.tokenize(case.NOTE)
        self.assertEqual(minted, [case.ATTACK_REF])
        self.assertRegex(minted[0], email.REF)

    def test_v1_check_passes_what_it_cannot_see(self):
        b = case.booking()
        self.assertIsNone(case.card_on_file_v1(
            {"refund_to": case.ATTACK_REF}, b))
        self.assertIsNotNone(case.card_on_file_v1(
            {"card_last4": "7731"}, b))

    def test_v2_reads_refund_to(self):
        b = case.booking()
        self.assertIsNotNone(case.card_on_file_v2(
            {"refund_to": case.ATTACK_REF}, b))
        self.assertIsNone(case.card_on_file_v2(
            {"refund_to": case.PAID_REF}, b))

    def test_june_26_and_july_refuse_before_the_desk(self):
        for cfg in (case.JUNE_26, case.JULY):
            r = case.replay(cfg)
            self.assertEqual(r.reached, "refused", cfg["name"])
            self.assertNotIn("desk", [s.stage for s in r.steps])

    def test_tagging_alone_is_a_signal_not_a_control(self):
        cfg = dict(case.JUNE_24, tagging=True)
        r = case.replay(cfg)
        self.assertTrue(r.signals)
        self.assertEqual(r.reached, "desk")


class TestBattery(unittest.TestCase):
    def test_v2_adds_one_attack_and_replaces_d02(self):
        spec = email.load_v2()
        ids = [a["id"] for a in spec["attack"]]
        self.assertEqual(len(ids), 62)
        self.assertEqual(len(set(ids)), 62)
        self.assertIn("T05", ids)

    def test_june_24_two_effects(self):
        outs, _ = email.run_v2(email.Options36())
        eff = sorted(o.id for o in outs if o.stage == "effect")
        self.assertEqual(eff, ["D02", "T05"])

    def test_destination_policy_closes_both(self):
        outs, _ = email.run_v2(email.Options36(destination=True))
        self.assertEqual([o for o in outs if o.stage == "effect"], [])
        self.assertEqual(sum(o.stage == "proposal" for o in outs), 6)

    def test_tagging_raises_signals(self):
        _, sig = email.run_v2(email.Options36(tagging=True,
                                              destination=True))
        self.assertEqual(sig, 4)

    def test_chapter_33_battery_unchanged(self):
        outs = B.run_battery()
        self.assertEqual(len(outs), 61)
        self.assertEqual([o for o in outs if o.stage == "effect"], [])


class TestGolden(unittest.TestCase):
    def test_june_set_never_tempts_from_untrusted_text(self):
        rows = {s: n for s, _, n in gaps.table(G.build())}
        self.assertEqual(rows["card in a tool result or document"], 0)
        self.assertEqual(rows["card named by the customer in chat"], 0)
        self.assertEqual(gaps.forbidden_on(G.build()), 640)

    def test_july_set_adds_the_hotel_case(self):
        tasks = gaps.july()
        self.assertEqual(len(tasks), 647)
        rows = {s: n for s, _, n in gaps.table(tasks)}
        self.assertEqual(rows["card in a tool result or document"], 1)


class TestBundle(unittest.TestCase):
    def test_lifecycle(self):
        log, store = bundles.lifecycle(41)
        self.assertIn("the author cannot sign it", log[1])
        self.assertTrue(log[-1].startswith("active at 14:12"))

    def test_short_shadow_does_not_activate(self):
        log, _ = bundles.lifecycle(20)
        self.assertTrue(log[-1].startswith("not activated"))

    def test_month_replay_refuses_only_the_hotel(self):
        seen, refused = bundles.replay_month(LINES)
        self.assertEqual(seen, 5968)
        self.assertEqual(refused, ["P-0624-HOTEL"])


class TestTrail(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(events("run")), month.RUNS)
        self.assertEqual(len(events("handoff")), month.HANDOFFS)
        self.assertEqual(len(events("execution")), 5967)
        self.assertEqual(len(events("change")), len(month.CHANGES))

    def test_chain_and_times(self):
        self.assertEqual(check_trail(LINES), [])
        at = [json.loads(x)["at"] for x in LINES]
        self.assertEqual(at, sorted(at))

    def test_hotel_rejected_by_teresa(self):
        a = [e for e in events("approval")
             if e["proposal"] == "P-0624-HOTEL"][0]
        self.assertEqual((a["approver"], a["verdict"]),
                         ("Teresa Alvarez", "rejected"))
        self.assertEqual(a["at"], "2026-06-24T08:31:22-05:00")

    def test_thirty_anchors_and_a_proof(self):
        self.assertEqual(len(HELD), 30)
        p = anchor.prove(LINES, 1000)
        self.assertTrue(anchor.verify(p["leaf"], p["path"],
                                      HELD[p["day"]]))
        self.assertFalse(anchor.verify("0" * 64, p["path"],
                                       HELD[p["day"]]))

    def test_rechain_passes_the_chain_and_fails_the_anchor(self):
        n = 32609
        re = anchor.rewrite(LINES, n, "verdict", "approved")
        self.assertEqual(check_trail(re), [])
        day = json.loads(LINES[n])["at"][:10]
        bad = anchor.check(re, HELD)
        self.assertEqual(bad[0], day)
        self.assertNotIn("2026-06-23", bad)


class TestPack(unittest.TestCase):
    def test_answers(self):
        a = PACK["answers"]
        self.assertEqual(a["P1"]["count"], 5967)
        self.assertEqual(a["P2"]["count"], 6001)
        self.assertEqual(a["P5"]["exceptions"], [])
        self.assertEqual(a["P5"]["proposed_elsewhere"], ["P-0624-HOTEL"])
        self.assertEqual(a["P4"]["edited"], 99)
        self.assertEqual(a["P7"]["handoffs"], 33)
        self.assertEqual(a["P11"]["exceptions"], [])

    def test_same_trail_same_seed_same_pack(self):
        again = P.generate(LINES, HELD, "2026-06", demo.SEED)
        self.assertEqual(again["digest"], PACK["digest"])

    def test_verifies_clean(self):
        self.assertEqual(P.verify(PACK, HELD), [])

    def test_sample_sixty_complete(self):
        items = PACK["sample"]["items"]
        self.assertEqual(len(items), 60)
        self.assertTrue(all(not P.check_sample(i, HELD) for i in items))

    def test_edited_answer_is_caught(self):
        forged = copy.deepcopy(PACK)
        forged["answers"]["P5"]["proposed_elsewhere"] = []
        self.assertIn("manifest: answers changed", P.verify(forged, HELD))

    def test_wrong_seal_is_caught(self):
        other = copy.deepcopy(PACK)
        other["seal"] = "0" * 64
        self.assertIn("seal does not verify", P.verify(other, HELD))

    def test_rechained_trail_pack_is_caught(self):
        re = anchor.rewrite(LINES, 32609, "verdict", "approved")
        rp = P.generate(re, anchor.anchors(re), "2026-06", demo.SEED)
        self.assertIn("anchors differ from the ones audit holds",
                      P.verify(rp, HELD))


class TestEvidence(unittest.TestCase):
    def test_june_24_does_not_hold(self):
        ok, why = A.holds(A.JUNE_24, "2026-06-24", [A.REBUTTAL])
        self.assertFalse(ok)
        self.assertIn("P-0624-HOTEL", why)

    def test_undercut_versus_silent(self):
        v = {e.eid: A.assess(e, "2026-06-24")[0] for e in A.JUNE_24}
        self.assertEqual(v, {"E1": "silent", "E2": "undercut",
                             "E3": "undercut", "E4": "silent",
                             "E5": "admissible"})

    def test_july_2_holds_and_owner_evidence_does_not_count(self):
        ok, why = A.holds(A.JULY_2, "2026-07-02", [A.REBUTTAL])
        self.assertTrue(ok)
        self.assertTrue(why.startswith("4 independent"))


class TestFinding(unittest.TestCase):
    def test_walk_closes_on_july_3(self):
        f, refusals = findings.walk([])
        self.assertEqual(f.state, "closed")
        self.assertEqual(f.log[-1][:3],
                         ("2026-07-03", "closed", "Elena Vasquez"))
        self.assertEqual(len(refusals), 2)

    def test_owner_cannot_close(self):
        f = findings.f0624()
        for s in ("contained", "triaged", "fix_live",
                  "evidence_submitted"):
            f.move(s, "2026-06-26", "Ben Carter")
        with self.assertRaises(findings.Refused):
            f.close("2026-07-03", "Ben Carter", [], A.JULY_2)

    def test_bad_pack_blocks_close(self):
        f = findings.f0624()
        for s in ("contained", "triaged", "fix_live",
                  "evidence_submitted"):
            f.move(s, "2026-06-26", "Ben Carter")
        with self.assertRaises(findings.Refused):
            f.close("2026-07-03", "Elena Vasquez", ["seal"], A.JULY_2)

    def test_auditor_cannot_do_the_owners_moves(self):
        f = findings.f0624()
        with self.assertRaises(findings.Refused):
            f.move("contained", "2026-06-24", "Elena Vasquez")


class TestCard(unittest.TestCase):
    def test_rows_name_an_owner(self):
        rows = scorecard.card(PACK, HELD, 9, 0, 62)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r[2] for r in rows))
        self.assertEqual(rows[3][1], "1 proposed, 0 paid")


class TestLive(unittest.TestCase):
    def test_replay_from_fixtures(self):
        out = live.run(live.FixtureTransport(live.FIXTURES),
                       record_fx=False)
        self.assertIn("model calls 20", out[-1])
        self.assertTrue(all(" 7731 0," in ln for ln in out
                            if "untagged:" in ln or "tagged:" in ln))

    def test_fixtures_hold_no_secret(self):
        for p in Path(live.FIXTURES).glob("*.json"):
            self.assertEqual(find_secrets(p.read_text(), fixture=True), [], p.name)


class TestDemo(unittest.TestCase):
    def test_parts_fit_the_page(self):
        for part in ("replay", "golden", "bundle", "evidence", "finding",
                     "live"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                demo.main(["--part", part])
            self.assertEqual(too_long(buf.getvalue()), [], part)


if __name__ == "__main__":
    unittest.main()
