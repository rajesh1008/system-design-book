"""Tests for the Lakeshore corpus v0. Offline, about one second."""
from __future__ import annotations

import json
import re
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from corpus.generate import (ANCHOR, CHANGE_TYPES, PILOT_CAP_USD,
                             PILOT_START, TABLES, generate, jsonl,
                             manifest, parse, write)

# Changing the generator changes this digest. That is deliberate: a
# chapter that depends on the corpus must say which digest it used.
PINNED_DIGEST = (
    "1eff42af7b9aaea13e893b18a2645e56b7cae6f55dfc9a43f0436a2315d1fd26")

T = generate(2026)


def index(table: str, key: str) -> dict:
    return {row[key]: row for row in T[table]}


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_bytes(self):
        again = generate(2026)
        for name in TABLES:
            self.assertEqual(jsonl(T[name]), jsonl(again[name]), name)

    def test_pinned_digest(self):
        self.assertEqual(manifest(T, 2026, "v0")["digest"], PINNED_DIGEST)

    def test_other_seed_differs(self):
        other = manifest(generate(7), 7, "v0")
        self.assertNotEqual(other["digest"], PINNED_DIGEST)

    def test_write_matches_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            m = write(Path(d), 2026, "v0")
            disk = json.loads((Path(d) / "manifest.json").read_text())
            self.assertEqual(disk, m)
            rows = (Path(d) / "refunds.jsonl").read_text().splitlines()
            self.assertEqual(len(rows), m["tables"]["refunds"]["rows"])

    def test_unknown_scale_refused(self):
        with self.assertRaises(ValueError):
            generate(2026, "huge")


class TestIntegrity(unittest.TestCase):
    def test_primary_keys_unique(self):
        keys = {"carriers": "carrier_id", "hotels": "hotel_id",
                "customers": "customer_id", "flights": "flight_id",
                "itineraries": "itinerary_id", "contacts": "contact_id",
                "changes": "change_id", "refunds": "refund_id",
                "settlement_lines": "line_id", "tickets": "ticket_id",
                "hotel_emails": "email_id", "memories": "memory_id",
                "policies": "policy_id"}
        for table, key in keys.items():
            ids = [r[key] for r in T[table]]
            self.assertEqual(len(ids), len(set(ids)), table)

    def test_foreign_keys_resolve(self):
        cust, flt = index("customers", "customer_id"), index(
            "flights", "flight_id")
        itin, con = index("itineraries", "itinerary_id"), index(
            "contacts", "contact_id")
        chg, ref = index("changes", "change_id"), index(
            "refunds", "refund_id")
        hotels, pol = index("hotels", "hotel_id"), index(
            "policies", "policy_id")
        carriers = {c["code"] for c in T["carriers"]}
        for f in T["flights"]:
            self.assertIn(f["carrier"], carriers)
        for i in T["itineraries"]:
            self.assertIn(i["customer_id"], cust)
            for s in i["segments"]:
                self.assertIn(s, flt)
            if i["hotel_id"]:
                self.assertIn(i["hotel_id"], hotels)
        for c in T["contacts"]:
            self.assertIn(c["itinerary_id"], itin)
            self.assertIn(c["customer_id"], cust)
        for c in T["changes"]:
            self.assertTrue(con[c["contact_id"]]["is_change"])
            self.assertIn(c["itinerary_id"], itin)
        for f in T["refunds"]:
            self.assertIn(f["change_id"], chg)
            self.assertIn(f["policy_id"], pol)
        for line in T["settlement_lines"]:
            self.assertIn(line["refund_id"], ref)
        for t in T["tickets"]:
            self.assertIn(t["itinerary_id"], itin)
        for m in T["memories"]:
            self.assertIn(m["customer_id"], cust)

    def test_ids_have_house_shapes(self):
        for i in T["itineraries"]:
            self.assertRegex(i["itinerary_id"], r"^LTG-\d{7}$")
        for c in T["carriers"]:
            self.assertRegex(c["code"], r"^X[A-Z]{2}$")

    def test_emails_are_reserved_domains(self):
        for c in T["customers"]:
            self.assertTrue(c["email"].endswith("@example.com"))
        for e in T["hotel_emails"]:
            self.assertTrue(e["from"].endswith(".example.org"))


class TestRatios(unittest.TestCase):
    def test_change_share_and_handlers(self):
        changes = T["changes"]
        self.assertEqual(len(changes) / len(T["contacts"]), 0.15)
        handled = Counter(c["handled_by"] for c in changes)
        self.assertAlmostEqual(handled["person"] / len(changes), 0.61)
        self.assertAlmostEqual(handled["agent"] / len(changes), 0.02)

    def test_twelve_change_types_all_present(self):
        self.assertEqual(len(CHANGE_TYPES), 12)
        self.assertEqual({c["type"] for c in T["changes"]},
                         set(CHANGE_TYPES))

    def test_refund_error_rate(self):
        refunds = T["refunds"]
        wrong = sum(1 for f in refunds if f["error"])
        self.assertAlmostEqual(wrong / len(refunds), 0.008, delta=0.0015)

    def test_handoff_flag_matches_handler(self):
        con = index("contacts", "contact_id")
        for c in T["changes"]:
            self.assertEqual(con[c["contact_id"]]["handed_to_person"],
                             c["handled_by"] == "person")

    def test_pilot_rules(self):
        for c in T["changes"]:
            if c["handled_by"] == "agent":
                self.assertGreaterEqual(parse(c["requested_at"]),
                                        PILOT_START)
        for f in T["refunds"]:
            if f["handled_by"] == "agent":
                self.assertLessEqual(f["amount_usd"], PILOT_CAP_USD)
                self.assertEqual(f["policy_id"], "refunds-v3")
            else:
                self.assertIsNone(f["permission_id"])


class TestAnchor(unittest.TestCase):
    def test_the_refund_that_happened_twice(self):
        lines = [x for x in T["settlement_lines"]
                 if x["itinerary_id"] == ANCHOR["itinerary"]]
        self.assertEqual(len(lines), 2)
        self.assertEqual({x["amount_usd"] for x in lines}, {412.60})
        self.assertEqual(len({x["refund_id"] for x in lines}), 1)
        gap = parse(lines[1]["credited_at"]) - parse(
            lines[0]["credited_at"])
        self.assertEqual(gap.total_seconds(), 3)
        self.assertEqual(lines[0]["credited_at"][:10], "2025-12-04")
        self.assertEqual([x["credit_ref"] for x in lines],
                         ["CR-00001", "CR-00002"])

    def test_anchor_has_no_permission_record_and_a_ticket(self):
        ref = next(f for f in T["refunds"]
                   if f["itinerary_id"] == ANCHOR["itinerary"])
        self.assertEqual((ref["handled_by"], ref["permission_id"],
                          ref["policy_id"]), ("agent", None, "refunds-v3"))
        tickets = [t for t in T["tickets"]
                   if t["itinerary_id"] == ANCHOR["itinerary"]]
        self.assertEqual(tickets[0]["opened_at"][:10], "2025-12-05")

    def test_anchor_flight_moved_eleven_hours_to_boston(self):
        itin = index("itineraries", "itinerary_id")[ANCHOR["itinerary"]]
        f = index("flights", "flight_id")[itin["segments"][0]]
        self.assertEqual((f["destination"], f["moved_hours"]), ("BOS", 11))


class TestContent(unittest.TestCase):
    def test_policies(self):
        v3 = index("policies", "policy_id")["refunds-v3"]
        self.assertEqual((v3["cap_usd"], v3["effective_from"]),
                         (1500.0, "2025-11-03"))

    def test_planted_instructions_are_flagged(self):
        flagged = [e for e in T["hotel_emails"] if e["contains_instruction"]]
        self.assertGreaterEqual(len(flagged), 3)
        for e in T["hotel_emails"]:
            has = "automated assistant" in e["body"]
            self.assertEqual(has, e["contains_instruction"])

    def test_memories_carry_provenance_and_expiry(self):
        for m in T["memories"]:
            self.assertIn(m["provenance"]["source"],
                          {"customer-stated", "agent-inferred",
                           "imported-crm"})
            self.assertGreater(m["expires_at"], m["created_at"])

    def test_timestamps_in_range_and_utc(self):
        pat = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        for c in T["contacts"]:
            self.assertRegex(c["at"], pat)
            self.assertTrue("2025-11-01" <= c["at"][:10] <= "2026-10-31")


if __name__ == "__main__":
    unittest.main()
