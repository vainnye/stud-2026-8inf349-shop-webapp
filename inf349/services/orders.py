from typing import Dict

from ..db import database_proxy
from ..models import Order, OrderProduct, Product
from .pricing import (
    compute_shipping_price,
    compute_total_price,
    compute_total_price_tax,
)


class OrderValidationError(Exception):
    """Raised when an order payload cannot be accepted."""

    def __init__(self, code: str, name: str, field: str = "product"):
        super().__init__(name)
        self.code = code
        self.name = name
        self.field = field


class OrderNotFoundError(Exception):
    """Raised when an order id does not exist in the database."""

    def __init__(self, order_id: int):
        super().__init__(f"Order {order_id} not found")
        self.order_id = order_id


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


def get_order(order_id: int) -> Order:
    """Fetch an order by id or raise OrderNotFoundError."""
    order = Order.get_or_none(Order.id == order_id)
    if order is None:
        raise OrderNotFoundError(order_id)
    return order


def order_to_dict(order: Order) -> Dict:
    """Serialize an order to the partie 1 JSON shape.

    Calculations are performed on the fly and never persisted.
    The contract uses `product` (singular) even though the schema supports
    multiple OrderProduct rows.
    """
    item = next(iter(order.items), None)
    product = (
        {"id": item.product_id, "quantity": item.quantity} if item else {}
    )

    return {
        "order": {
            "shipping_information": order.shipping_information or {},
            "credit_card": order.credit_card or {},
            "paid": order.paid,
            "transaction": order.transaction or {},
            "product": product,
            "total_price": compute_total_price(order),
            "total_price_tax": compute_total_price_tax(order),
            "shipping_price": compute_shipping_price(order),
            "email": order.email,
            "id": order.id,
        }
    }
