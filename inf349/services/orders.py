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

    def __init__(self, code: str, name: str, field: str = "product",
                 remote_relay: bool = False):
        super().__init__(name)
        self.code = code
        self.name = name
        self.field = field
        # When True, the HTTP layer should emit the response literally
        # ({field: {code, name}}) without the `errors` wrapper, to match the
        # PDF example (page 10) for card-declined responses relayed from the
        # remote payment service.
        self.remote_relay = remote_relay


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
_MISSING_ORDER_FIELDS = (
    "missing-fields",
    "Il manque un ou plusieurs champs qui sont obligatoires",
)


REQUIRED_SHIPPING_FIELDS = (
    "country",
    "address",
    "postal_code",
    "city",
    "province",
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


def _raise_order_missing():
    code, name = _MISSING_ORDER_FIELDS
    raise OrderValidationError(code, name, field="order")


def _valid_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _validate_shipping_information(raw):
    if not isinstance(raw, dict):
        return None
    cleaned = {}
    for key in REQUIRED_SHIPPING_FIELDS:
        value = raw.get(key)
        if not _valid_non_empty_string(value):
            return None
        cleaned[key] = value
    return cleaned


def update_client_info(order_id: int, payload: Dict) -> Order:
    """Update email and shipping_information on an existing order.

    Raises OrderNotFoundError if the order id does not exist.
    Raises OrderValidationError(code="missing-fields", field="order") if the
    payload is missing any required field.

    Any other key in the payload is ignored: this endpoint cannot modify
    id, product, paid, transaction, shipping_price, total_price or
    total_price_tax.
    """
    order = get_order(order_id)

    order_data = payload.get("order") if isinstance(payload, dict) else None
    if not isinstance(order_data, dict):
        _raise_order_missing()

    email = order_data.get("email")
    if not _valid_non_empty_string(email):
        _raise_order_missing()

    shipping = _validate_shipping_information(
        order_data.get("shipping_information")
    )
    if shipping is None:
        _raise_order_missing()

    order.email = email
    order.shipping_information = shipping
    order.save()

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
