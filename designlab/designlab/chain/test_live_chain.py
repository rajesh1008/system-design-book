"""Live: real small-model output through the chain (two short calls)."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveChain(unittest.TestCase):
    def test_model_words_never_grant(self):
        from chain.live import run
        lines = run()
        text = "\n".join(lines)
        # The claimed approval must stop before any permission exists.
        claimed = text.split("claimed approval:")[1]
        self.assertNotIn("six states", claimed.split("spent")[0])
        self.assertTrue(lines[-1].startswith("spent $0.0"))


if __name__ == "__main__":
    unittest.main()
