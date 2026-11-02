import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from rules import VERSIONS, change_fee, in_effect

CDT = ZoneInfo("America/Chicago")


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=CDT)


class FeeRules(unittest.TestCase):
    def test_may_ticket_gets_version_two(self):
        self.assertEqual(change_fee(at("2026-05-02T11:00")), 100)

    def test_april_ticket_gets_2025_fee(self):
        self.assertEqual(change_fee(at("2026-04-12T09:30")), 75)

    def test_as_of_uses_local_issue_date(self):
        # issued April 30, 8:15 p.m. CDT: the 2025 page is in effect
        self.assertEqual(change_fee(at("2026-04-30T20:15")), 75)

    def test_may_first_midnight_local(self):
        self.assertEqual(change_fee(at("2026-05-01T00:00")), 100)

    def test_one_version_at_a_time(self):
        self.assertEqual(in_effect(at("2026-05-01T08:00"))["id"],
                         "xpa-main-v2")

    def test_fees_are_whole_dollars(self):
        self.assertTrue(all(isinstance(v["fee"], int) for v in VERSIONS))


if __name__ == "__main__":
    unittest.main()
