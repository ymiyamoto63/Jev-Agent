import unittest

from shop.config import DEFAULTS, load_config


class PageSizeTest(unittest.TestCase):
    def test_default(self):
        self.assertEqual(DEFAULTS["page_size"], 25)
        self.assertEqual(load_config({})["page_size"], 25)
