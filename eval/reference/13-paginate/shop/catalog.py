from dataclasses import dataclass


@dataclass
class Product:
    sku: str
    name: str
    price: float
    stock: int = 0


PRODUCTS = [
    Product("ABC-0001", "Coffee beans", 12.50, 40),
    Product("ABC-0002", "Green tea", 8.00, 0),
    Product("DEF-0010", "Mug", 9.99, 15),
    Product("DEF-0011", "Kettle", 34.00, 3),
    Product("GHI-0100", "Filter papers", 3.25, 200),
]


def search_products(query, products=None):
    products = PRODUCTS if products is None else products
    q = query.lower()
    return [p for p in products if q in p.name.lower() or q in p.sku.lower()]


def paginate(items, page, size):
    """Return the items on 1-indexed `page`."""
    if page < 1 or size < 1:
        raise ValueError("page and size must be >= 1")
    start = (page - 1) * size
    return items[start:start + size]


def in_stock(products=None):
    products = PRODUCTS if products is None else products
    return [p for p in products if p.stock > 0]
