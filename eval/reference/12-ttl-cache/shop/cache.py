import functools
import time
from collections import OrderedDict


def ttl_lru_cache(maxsize=128, ttl=60.0, clock=time.monotonic):
    def deco(fn):
        data = OrderedDict()
        stats = {"hits": 0, "misses": 0}

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = clock()
            if key in data and now - data[key][0] < ttl:
                data.move_to_end(key)
                stats["hits"] += 1
                return data[key][1]
            stats["misses"] += 1
            value = fn(*args, **kwargs)
            data[key] = (now, value)
            data.move_to_end(key)
            while len(data) > maxsize:
                data.popitem(last=False)
            return value

        def cache_info():
            return {"hits": stats["hits"], "misses": stats["misses"], "size": len(data)}

        def cache_clear():
            data.clear()
            stats.update(hits=0, misses=0)

        wrapper.cache_info, wrapper.cache_clear = cache_info, cache_clear
        return wrapper
    return deco
