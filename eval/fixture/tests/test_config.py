import unittest

from shop.config import DEFAULTS, load_config


class ConfigTest(unittest.TestCase):
    def test_default_page_size(self):
        self.assertEqual(DEFAULTS["page_size"], 20)

    def test_env_override(self):
        self.assertEqual(load_config({"SHOP_PAGE_SIZE": "5"})["page_size"], 5)
