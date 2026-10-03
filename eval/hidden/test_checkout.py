import unittest

from shop.money import LineItem
from shop.orders import Order, OrderRepository, checkout


class CheckoutTest(unittest.TestCase):
    def test_coupon_applied_once(self):
        self.assertAlmostEqual(checkout(Order("a", [LineItem(100.0, 1)], "TENOFF")), 90.0)
        self.assertAlmostEqual(checkout(Order("a", [LineItem(30.0, 1)], "HALF")), 15.0)

    def test_no_coupon(self):
        self.assertAlmostEqual(checkout(Order("a", [LineItem(100.0, 1)])), 100.0)
        self.assertAlmostEqual(checkout(Order("a", [LineItem(100.0, 1)], "BOGUS")), 100.0)

    def test_saved_total(self):
        repo = OrderRepository()
        repo.save(Order("bob", [LineItem(100.0, 1)], "TENOFF"))
        self.assertAlmostEqual(repo.conn.execute("SELECT total FROM orders").fetchone()[0], 90.0)
