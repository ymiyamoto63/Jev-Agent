import unittest
from decimal import Decimal

from shop.money import LineItem, compute_total


def dec(x):
    return Decimal(str(x))


class RoundingTest(unittest.TestCase):
    def test_half_up(self):
        self.assertEqual(dec(compute_total([LineItem(1.15, 1)], 50)), Decimal("0.58"))
        self.assertEqual(dec(compute_total([LineItem(10.05, 1)], 50)), Decimal("5.03"))

    def test_regular(self):
        self.assertEqual(dec(compute_total([LineItem(19.99, 3)], 10)), Decimal("53.97"))
        self.assertEqual(dec(compute_total([LineItem(0.10, 3)])), Decimal("0.30"))
        self.assertEqual(dec(compute_total([LineItem(12.50, 40), LineItem(9.99, 15)])), Decimal("649.85"))
