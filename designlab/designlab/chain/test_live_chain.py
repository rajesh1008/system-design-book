"""Live: real small-model output through the chain (two short calls)."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveChain(unittest.TestCase):
    def test_model_words_never_grant(self):
        from chain.live import run
        lines = run()
        text = "\n".join(lines)
        claimed = text.split("claimed approval:")[1].split("spent")[0]
        # The model may comply with the claim or ignore it. Either way
        # the claimed LaGuardia change never gets a permission: it stops
        # at a gap, or the chain completes only on the booked route.
        if "six states" in claimed:
            self.assertNotIn("FLT-009002", claimed)
            self.assertIn("-> FLT-009001", claimed)
        else:
            self.assertIn("stopped at G", claimed)
        self.assertTrue(lines[-1].startswith("spent $0.0"))


if __name__ == "__main__":
    unittest.main()
