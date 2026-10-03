import unittest
from datetime import date

from shop.dates import add_months


class AddMonthsTest(unittest.TestCase):
    def test_cases(self):
        cases = [
            (date(2024, 1, 15), 1, date(2024, 2, 15)),
            (date(2024, 1, 31), 1, date(2024, 2, 29)),
            (date(2023, 1, 31), 1, date(2023, 2, 28)),
            (date(2024, 3, 31), -1, date(2024, 2, 29)),
            (date(2024, 5, 31), -13, date(2023, 4, 30)),
            (date(2024, 11, 10), 3, date(2025, 2, 10)),
            (date(2024, 8, 31), 1, date(2024, 9, 30)),
        ]
        for d, n, want in cases:
            with self.subTest(d=d, n=n):
                self.assertEqual(add_months(d, n), want)
