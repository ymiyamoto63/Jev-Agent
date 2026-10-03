import unittest

from shop.catalog import paginate


class PaginateTest(unittest.TestCase):
    def test_pages(self):
        items = list(range(10))
        self.assertEqual(paginate(items, 1, 3), [0, 1, 2])
        self.assertEqual(paginate(items, 2, 3), [3, 4, 5])
        self.assertEqual(paginate(items, 4, 3), [9])
        self.assertEqual(paginate(items, 5, 3), [])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            paginate([1], 0, 3)
