from typing import Dict

from ..db import database_proxy
from ..models import Order, OrderProduct, Product


class OrderValidationError(Exception):
    """Raised when an order payload cannot be accepted."""

    def __init__(self, code: str, name: str, field: str = "product"):
        super().__init__(name)
        self.code = code
        self.name = name
        self.field = field


_MISSING = (
    "missing-fields",
    "La création d'une commande nécessite un produit",
)
_OUT_OF_STOCK = (
    "out-of-inventory",
    "Le produit demandé n'est pas en inventaire",
)


def _raise(info):
    code, name = info
    raise OrderValidationError(code, name)


def create_order(payload: Dict) -> Order:
    """Validate the payload and persist a new order with a single product line.

    Raises OrderValidationError for any payload / domain validation issue.
    """
    if not isinstance(payload, dict):
        _raise(_MISSING)

    product_data = payload.get("product")
    if not isinstance(product_data, dict):
        _raise(_MISSING)

    pid = product_data.get("id")
    quantity = product_data.get("quantity")

    if pid is None or quantity is None:
        _raise(_MISSING)

    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
        _raise(_MISSING)

    product = Product.get_or_none(Product.id == pid)
    if product is None:
        _raise(_MISSING)

    if not product.in_stock:
        _raise(_OUT_OF_STOCK)

    with database_proxy.atomic():
        order = Order.create()
        OrderProduct.create(order=order, product=product, quantity=quantity)

    return order
