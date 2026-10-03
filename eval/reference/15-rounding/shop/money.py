from dataclasses import dataclass


@dataclass
class LineItem:
    price: float
    qty: int


def compute_total(items, discount_pct=0):
    """Order total after a percentage discount, rounded to cents (half-up, like our invoices)."""
    from decimal import ROUND_HALF_UP, Decimal
    subtotal = sum(Decimal(str(i.price)) * i.qty for i in items)
    total = subtotal * (1 - Decimal(str(discount_pct)) / 100)
    return float(total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def format_price(amount, currency="USD"):
    symbol = {"USD": "$", "EUR": "€", "JPY": "¥"}.get(currency, "")
    return f"{symbol}{amount:,.2f}"
