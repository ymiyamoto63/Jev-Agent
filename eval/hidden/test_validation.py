import unittest

from shop.catalog import PRODUCTS, Product


class ValidationTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(Product("XYZ-1234", "ok", 0).price, 0)
        self.assertEqual(len(PRODUCTS), 5)

    def test_negative_price(self):
        with self.assertRaises(ValueError):
            Product("XYZ-1234", "bad", -0.01)

    def test_bad_sku(self):
        for sku in ("xyz-1234", "XY-1234", "XYZ-123", "XYZ1234", "XYZ-12345", ""):
            with self.subTest(sku=sku), self.assertRaises(ValueError):
                Product(sku, "bad", 1.0)
