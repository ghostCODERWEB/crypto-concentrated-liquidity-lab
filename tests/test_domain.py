import unittest, copy, json
from decimal import Decimal
from pathlib import Path
from cryptolab import analyze
from cryptolab.engine import *

EXAMPLE = json.loads(Path("examples/input.json").read_text())


class DomainTests(unittest.TestCase):
    def test_outside_inventory(self):
        x, y = inventory(1000, 64, 144, 160)
        self.assertEqual(x, 0)
        self.assertGreater(y, 0)
        x, y = inventory(1000, 64, 144, 50)
        self.assertEqual(y, 0)
        self.assertGreater(x, 0)

    def test_fee_conservation(self):
        self.assertEqual(Decimal(analyze(EXAMPLE)["total_allocated_fees"]), 50)

    def test_segments(self):
        self.assertEqual(analyze(EXAMPLE)["segments"][1]["active_liquidity"], "1500")

    def test_initial_no_loss(self):
        for p in analyze(EXAMPLE)["trajectory"][0]["positions"]:
            self.assertAlmostEqual(float(p["relative_loss"]), 0)

    def test_unfunded_fee(self):
        d = copy.deepcopy(EXAMPLE)
        d["trajectory"] = [{"price": "1000", "fee_token1": "1"}]
        with self.assertRaises(ValueError):
            analyze(d)
