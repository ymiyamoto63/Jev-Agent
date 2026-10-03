import unittest

from shop.catalog import find_products


class RenameTest(unittest.TestCase):
    def test_find_products(self):
        self.assertEqual([p.sku for p in find_products("mug")], ["DEF-0010"])

    def test_cli_still_works(self):
        from shop.cli import main
        self.assertEqual(main(["list", "--query", "tea"]), 0)
