import unittest
from decimal import Decimal

from shop.pricing import price_order

CASES = [
    ([("A", "12.50", 2)], "standard", None, "32.00"),
    ([("A", "3.33", 10)], "standard", None, "38.64"),
    ([("A", "3.33", 50)], "gold", None, "145.35"),
    ([("A", "19.99", 3), ("B", "0.99", 12)], "platinum", "SAVE10", "64.70"),
    ([("A", "45.00", 1)], "gold", "SAVE10", "50.65"),
    ([("A", "60.00", 2)], "standard", "SAVE10", "110.00"),
    ([("A", "20.00", 1)], "standard", "FREESHIP", "20.00"),
    ([("A", "104.00", 1)], "platinum", None, "105.80"),
    ([], "gold", None, "7.00"),
    ([("A", "1.05", 11)], "standard", None, "17.97"),
]


class PricingTest(unittest.TestCase):
    def test_cases(self):
        for lines, tier, coupon, want in CASES:
            with self.subTest(lines=lines, tier=tier, coupon=coupon):
                got = price_order(lines, tier, coupon)
                self.assertIsInstance(got, Decimal)
                self.assertEqual(got, Decimal(want))
