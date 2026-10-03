import threading


class OutOfStock(Exception):
    pass


class StockCounter:
    def __init__(self, stock, on_reserve=None):
        self._stock = dict(stock)
        self._on_reserve = on_reserve or (lambda sku, qty: None)  # audit hook; writes to the audit DB in production
        self._audit_lock = threading.Lock()

    def available(self, sku):
        return self._stock.get(sku, 0)

    def reserve(self, sku, qty):
        available = self._stock.get(sku, 0)
        if qty > available:
            raise OutOfStock(sku)
        with self._audit_lock:
            self._on_reserve(sku, qty)
        self._stock[sku] = available - qty
        return self._stock[sku]
