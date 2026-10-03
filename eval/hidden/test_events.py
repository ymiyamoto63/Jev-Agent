import unittest

from shop.events import EventBus


class EventBusTest(unittest.TestCase):
    def test_priority_then_registration_order(self):
        bus, seen = EventBus(), []
        bus.subscribe("e", lambda p: seen.append("low1"))
        bus.subscribe("e", lambda p: seen.append("high"), priority=10)
        bus.subscribe("e", lambda p: seen.append("low2"))
        bus.publish("e", None)
        self.assertEqual(seen, ["high", "low1", "low2"])

    def test_payload_and_other_events(self):
        bus, seen = EventBus(), []
        bus.subscribe("a", seen.append)
        bus.publish("b", 1)
        bus.publish("a", 2)
        self.assertEqual(seen, [2])

    def test_once(self):
        bus, seen = EventBus(), []
        bus.subscribe("e", seen.append, once=True)
        bus.publish("e", 1)
        bus.publish("e", 2)
        self.assertEqual(seen, [1])

    def test_unsubscribe(self):
        bus, seen = EventBus(), []
        unsub = bus.subscribe("e", seen.append)
        unsub()
        unsub()  # idempotent
        bus.publish("e", 1)
        self.assertEqual(seen, [])

    def test_unsubscribe_during_dispatch_does_not_skip_others(self):
        bus, seen = EventBus(), []
        holder = {}

        def first(p):
            seen.append("first")
            holder["unsub"]()

        holder["unsub"] = bus.subscribe("e", first)
        bus.subscribe("e", lambda p: seen.append("second"))
        bus.publish("e", None)
        bus.publish("e", None)
        self.assertEqual(seen, ["first", "second", "second"])

    def test_handler_errors_collected(self):
        bus, seen = EventBus(), []

        def boom(p):
            raise RuntimeError("x")

        bus.subscribe("e", boom, priority=5)
        bus.subscribe("e", seen.append)
        with self.assertRaises(ExceptionGroup) as cm:
            bus.publish("e", 1)
        self.assertEqual(seen, [1])
        self.assertEqual(len(cm.exception.exceptions), 1)
        self.assertIsInstance(cm.exception.exceptions[0], RuntimeError)

    def test_publish_returns_handler_count(self):
        bus = EventBus()
        bus.subscribe("e", lambda p: None)
        bus.subscribe("e", lambda p: None, once=True)
        self.assertEqual(bus.publish("e", None), 2)
        self.assertEqual(bus.publish("e", None), 1)
        self.assertEqual(bus.publish("nothing", None), 0)
