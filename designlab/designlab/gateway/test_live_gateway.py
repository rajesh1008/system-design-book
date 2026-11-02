"""Live: clean and poisoned CRX description on the small model."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveGateway(unittest.TestCase):
    def test_poisoned_description_never_forwarded(self):
        from gateway.live import run, summarize
        res = run()
        self.assertEqual(len(res["clean"]), 6)
        self.assertEqual(len(res["poisoned"]), 6)
        # Whatever the model proposes, the rejected entry is refused
        # at the gateway and the supplier's server sees nothing.
        for arm in ("clean", "poisoned"):
            for r in res[arm]:
                self.assertEqual(r["gateway"], "not_approved")
        self.assertEqual(res["forwarded"], 0)
        self.assertLess(res["spent"], 0.05)
        self.assertTrue(summarize(res)[0].startswith("model "))


if __name__ == "__main__":
    unittest.main()
