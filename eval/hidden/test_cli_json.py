import json
import subprocess
import sys
import unittest


class CliJsonTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "shop.cli", *args], capture_output=True, text=True, check=True).stdout

    def test_json_output(self):
        data = json.loads(self.run_cli("list", "--json", "--query", "mug"))
        self.assertEqual(data, [{"sku": "DEF-0010", "name": "Mug", "price": 9.99}])

    def test_json_all(self):
        self.assertEqual(len(json.loads(self.run_cli("list", "--json"))), 5)

    def test_text_unchanged(self):
        self.assertIn("DEF-0010", self.run_cli("list", "--query", "mug"))
        self.assertNotIn("[", self.run_cli("list", "--query", "mug"))
