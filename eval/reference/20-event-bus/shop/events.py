import itertools


class EventBus:
    def __init__(self):
        self._subs = {}
        self._seq = itertools.count()

    def subscribe(self, event, handler, priority=0, once=False):
        entry = {"handler": handler, "priority": priority, "seq": next(self._seq), "once": once, "active": True}
        self._subs.setdefault(event, []).append(entry)

        def unsubscribe():
            if entry["active"]:
                entry["active"] = False
                self._subs[event].remove(entry)
        return unsubscribe

    def publish(self, event, payload):
        entries = sorted(self._subs.get(event, []), key=lambda e: (-e["priority"], e["seq"]))
        errors, called = [], 0
        for e in entries:
            if not e["active"]:
                continue
            if e["once"]:
                e["active"] = False
                self._subs[event].remove(e)
            called += 1
            try:
                e["handler"](payload)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup(f"{len(errors)} handler(s) failed", errors)
        return called
