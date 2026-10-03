import unittest
from datetime import date

from shop.dates import add_months


class DatesTest(unittest.TestCase):
    def test_add_months_simple(self):
        self.assertEqual(add_months(date(2024, 1, 15), 1), date(2024, 2, 15))

    def test_add_months_year_wrap(self):
        self.assertEqual(add_months(date(2024, 11, 10), 3), date(2025, 2, 10))

    def test_add_months_end_of_month(self):
        self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))
