"""Chapter 44's extension to the Capacity Model: the approval desk."""
import math
import unittest

from .approvals import (backlog_after, drain_hours, offered, p_late,
                        seats_for)


class Approvals(unittest.TestCase):
    def test_chapter_43_storm_hour(self):
        self.assertAlmostEqual(offered(2238, 2), 74.6)
        self.assertEqual(seats_for(2238, 2, 60), 75)

    def test_more_seats_fewer_late(self):
        self.assertLess(p_late(80, 2238, 2, 60), p_late(76, 2238, 2, 60))

    def test_overloaded_desk_never_drains(self):
        self.assertTrue(math.isinf(drain_hours(100, 2, 5, 30)))

    def test_drain(self):
        self.assertAlmostEqual(drain_hours(600, 10, 2, 0), 2.0)

    def test_backlog_carries(self):
        self.assertEqual(backlog_after([100, 100, 0], [1, 1, 10], 1),
                         [40.0, 80.0, 0.0])


if __name__ == "__main__":
    unittest.main()
