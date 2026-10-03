import unittest

from shop.cache import ttl_lru_cache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.calls = []

    def make(self, **kw):
        @ttl_lru_cache(clock=self.clock, **kw)
        def f(x, y=0):
            self.calls.append((x, y))
            return x + y
        return f

    def test_hits_and_misses(self):
        f = self.make(maxsize=10, ttl=60)
        self.assertEqual(f(1), 1)
        self.assertEqual(f(1), 1)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(f.cache_info(), {"hits": 1, "misses": 1, "size": 1})

    def test_kwargs_are_part_of_key(self):
        f = self.make(maxsize=10, ttl=60)
        f(1, y=2)
        f(1, y=3)
        f(1, y=2)
        self.assertEqual(len(self.calls), 2)

    def test_ttl_expiry(self):
        f = self.make(maxsize=10, ttl=5)
        f(1)
        self.clock.t = 4.9
        f(1)
        self.assertEqual(len(self.calls), 1)
        self.clock.t = 5.0
        f(1)
        self.assertEqual(len(self.calls), 2)

    def test_lru_eviction_respects_recency(self):
        f = self.make(maxsize=2, ttl=60)
        f(1)
        f(2)
        f(1)      # 1 is now most recent
        f(3)      # evicts 2
        self.assertEqual(f.cache_info()["size"], 2)
        f(1)
        self.assertEqual(len(self.calls), 3)
        f(2)
        self.assertEqual(len(self.calls), 4)

    def test_clear(self):
        f = self.make(maxsize=2, ttl=60)
        f(1)
        f.cache_clear()
        self.assertEqual(f.cache_info(), {"hits": 0, "misses": 0, "size": 0})
        f(1)
        self.assertEqual(len(self.calls), 2)
