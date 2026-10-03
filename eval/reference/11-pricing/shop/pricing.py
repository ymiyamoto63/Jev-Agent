from decimal import ROUND_HALF_UP, Decimal

C = Decimal("0.01")


def _q(x):
    return x.quantize(C, rounding=ROUND_HALF_UP)


def price_order(lines, customer_tier, coupon=None):
    amount = Decimal(0)
    for _sku, unit, qty in lines:
        line = Decimal(unit) * qty
        if qty >= 50:
            line *= Decimal("0.90")
        elif qty >= 10:
            line *= Decimal("0.95")
        amount += _q(line)
    tier = {"gold": Decimal("0.03"), "platinum": Decimal("0.05")}.get(customer_tier, Decimal(0))
    amount = _q(amount * (1 - tier))
    if coupon == "SAVE10" and amount >= 50:
        amount = max(amount - 10, Decimal(0))
    if amount < 100 and coupon != "FREESHIP":
        amount += Decimal("7.00")
    return _q(amount)
