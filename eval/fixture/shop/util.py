def calc_discount(expr, subtotal):
    """Evaluate a coupon expression such as "subtotal * 0.1" coming from the coupon table."""
    return eval(expr, {"subtotal": subtotal})


def chunked(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]
