"""pytest/unittest entry: every non-known-limit case must pass."""
import unittest
from run_eval import run
from tests.cases import CASES

class T(unittest.TestCase):
    def test_cases(self):
        for cid, g, inp, refs, exp, limit in CASES:
            with self.subTest(cid):
                act = run(g, inp, refs)
                if limit:
                    continue  # documented limitation, reported in RESULTS.md
                self.assertEqual(act, exp)
if __name__ == "__main__":
    unittest.main()
