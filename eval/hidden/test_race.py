import threading
import time
import unittest

from shop.inventory import OutOfStock, StockCounter


class RaceTest(unittest.TestCase):
    def run_trial(self):
        counter = StockCounter({"X": 10}, on_reserve=lambda sku, qty: time.sleep(0.001))
        ok = []
        lock = threading.Lock()

        def worker():
            for _ in range(5):
                try:
                    counter.reserve("X", 1)
                    with lock:
                        ok.append(1)
                except OutOfStock:
                    pass

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return len(ok), counter.available("X")

    def test_no_oversell(self):
        for _ in range(5):
            self.assertEqual(self.run_trial(), (10, 0))

    def test_out_of_stock_still_raised(self):
        c = StockCounter({"X": 1})
        c.reserve("X", 1)
        with self.assertRaises(OutOfStock):
            c.reserve("X", 1)
