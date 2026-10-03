import unittest

from shop.catalog import search_products


class CatalogTest(unittest.TestCase):
    def test_search_by_name(self):
        self.assertEqual([p.sku for p in search_products("mug")], ["DEF-0010"])

    def test_search_by_sku(self):
        self.assertEqual(len(search_products("abc")), 2)
