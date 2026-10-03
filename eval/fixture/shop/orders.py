import sqlite3

from .money import LineItem, compute_total
from .util import calc_discount

COUPONS = {"TENOFF": 10, "HALF": 50}


class Order:
    def __init__(self, customer, items, coupon=None):
        if any(i.qty <= 0 for i in items):
            raise ValueError("Invalid quantitiy")
        self.customer = customer
        self.items = items
        self.coupon = coupon

    def discount_pct(self):
        return COUPONS.get(self.coupon, 0)

    def total(self):
        return compute_total(self.items, self.discount_pct())


def checkout(order):
    """Amount to charge for an order."""
    amount = order.total()
    if order.coupon:
        amount = amount * (1 - order.discount_pct() / 100)
    return round(amount, 2)


class OrderRepository:
    def __init__(self, db_path=":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer TEXT, total REAL)")

    def save(self, order):
        cur = self.conn.execute("INSERT INTO orders (customer, total) VALUES (?, ?)", (order.customer, checkout(order)))
        return cur.lastrowid

    def find_by_customer(self, customer):
        return self.conn.execute(f"SELECT id, customer, total FROM orders WHERE customer = '{customer}'").fetchall()

    def apply_custom_coupon(self, expr, subtotal):
        return calc_discount(expr, subtotal)
