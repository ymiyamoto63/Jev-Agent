from dataclasses import dataclass


@dataclass
class LineItem:
    price: float
    qty: int


def compute_total(items, discount_pct=0):
    """Order total after a percentage discount, rounded to cents (half-up, like our invoices)."""
    subtotal = sum(i.price * i.qty for i in items)
    total = subtotal * (1 - discount_pct / 100)
    return round(total, 2)


def format_price(amount, currency="USD"):
    symbol = {"USD": "$", "EUR": "€", "JPY": "¥"}.get(currency, "")
    return f"{symbol}{amount:,.2f}"
