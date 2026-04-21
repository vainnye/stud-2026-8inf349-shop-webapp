import json
from typing import Dict, Optional

from ..db import database_proxy
from ..models import Order, OrderProduct, Product
from .pricing import (
    compute_shipping_price,
    compute_total_price,
    compute_total_price_tax,
)

# Redis cache key prefix for paid orders.
_REDIS_KEY_PREFIX = "order:"


def _redis_url() -> Optional[str]:
    """Return REDIS_URL from the current Flask app config, or None."""
    try:
        from flask import current_app
        return current_app.config.get("REDIS_URL")
    except RuntimeError:
        return None  # no app context (unit tests calling services directly)


def _get_redis_client(redis_url: Optional[str]):
    """Return a Redis client for redis_url, or None if unavailable."""
    if not redis_url:
        return None
    try:
        import redis as _redis
        return _redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


class CachedOrder:
    """Proxy returned by get_order() when the order is served from Redis.

    Only paid orders are cached. Exposes the attributes read by
    pay_order(), update_client_info(), and order_to_dict() so those
    functions work transparently without touching PostgreSQL.

    save() raises already-paid because cached orders are immutable.
    """

    def __init__(self, cached_dict: Dict):
        self._dict = cached_dict
        o = cached_dict["order"]
        self.id = o["id"]
        self.paid = o["paid"]
        self.email = o.get("email")
        self.shipping_information = o.get("shipping_information") or None
        self.credit_card = o.get("credit_card") or None
        self.transaction = o.get("transaction") or None

    def save(self, *args, **kwargs):
        raise OrderValidationError(
            "already-paid", "La commande a déjà été payée.", field="order",
        )

    def to_dict(self) -> Dict:
        return self._dict


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


def _normalize_product_list(payload: Dict):
    """Return a non-empty list of raw {id, quantity} dicts, or None.

    Accepts both formats:
      - {"products": [{"id": 1, "quantity": 2}, ...]}   (partie 2, multi)
      - {"product":  {"id": 1, "quantity": 2}}           (partie 1, rétrocompat)

    Any other shape returns None (caller raises missing-fields).
    """
    if "products" in payload:
        items = payload["products"]
        if not isinstance(items, list) or len(items) == 0:
            return None
        return items
    product = payload.get("product")
    if isinstance(product, dict):
        return [product]
    return None


def create_order(payload: Dict) -> Order:
    """Validate the payload and persist a new order with one or more product lines.

    Accepts {"product": {...}} (single, rétrocompat) and
    {"products": [...]} (multi-produits, partie 2).

    Raises OrderValidationError for any payload / domain validation issue.
    """
    if not isinstance(payload, dict):
        _raise(_MISSING)

    raw_items = _normalize_product_list(payload)
    if raw_items is None:
        _raise(_MISSING)

    # Validate every item before touching the DB.
    validated = []
    for item in raw_items:
        if not isinstance(item, dict):
            _raise(_MISSING)

        pid = item.get("id")
        quantity = item.get("quantity")

        if pid is None or quantity is None:
            _raise(_MISSING)

        if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            _raise(_MISSING)

        product = Product.get_or_none(Product.id == pid)
        if product is None:
            _raise(_MISSING)

        if not product.in_stock:
            _raise(_OUT_OF_STOCK)

        validated.append((product, quantity))

    with database_proxy.atomic():
        order = Order.create()
        for product, quantity in validated:
            OrderProduct.create(order=order, product=product, quantity=quantity)

    return order


def get_order(order_id: int) -> Order:
    """Fetch an order from Redis cache (paid orders) or PostgreSQL.

    Redis is always checked first. On a cache hit a CachedOrder proxy is
    returned and PostgreSQL is never contacted — satisfying the resilience
    requirement: GET /order/<id> must work without Postgres when cached.

    On any Redis error the call falls through to PostgreSQL silently.
    """
    client = _get_redis_client(_redis_url())
    if client is not None:
        try:
            raw = client.get(f"{_REDIS_KEY_PREFIX}{order_id}")
            if raw:
                return CachedOrder(json.loads(raw))
        except Exception:
            pass  # Redis unavailable → fall through to Postgres

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
    Raises OrderValidationError(code="already-paid") if the order is paid
    (paid orders are immutable, whether served from cache or Postgres).
    Raises OrderValidationError(code="missing-fields", field="order") if the
    payload is missing any required field.

    Any other key in the payload is ignored: this endpoint cannot modify
    id, products, paid, transaction, shipping_price, total_price or
    total_price_tax.
    """
    order = get_order(order_id)

    if order.paid:
        raise OrderValidationError(
            "already-paid", "La commande a déjà été payée.", field="order",
        )

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
    """Serialize an order to the partie 2 JSON shape.

    Pure function — no side effects, no cache writes.

    If order is a CachedOrder (Redis hit), return the pre-cached dict
    directly — PostgreSQL is never touched in that path.

    For real Order objects, calculations are performed on the fly and
    never persisted.
    """
    # Fast path: order already fully serialized from Redis cache.
    if isinstance(order, CachedOrder):
        return order.to_dict()

    products = [
        {"id": item.product_id, "quantity": item.quantity}
        for item in order.items
    ]

    return {
        "order": {
            "shipping_information": order.shipping_information or {},
            "credit_card": order.credit_card or {},
            "paid": order.paid,
            "transaction": order.transaction or {},
            "products": products,
            "total_price": compute_total_price(order),
            "total_price_tax": compute_total_price_tax(order),
            "shipping_price": compute_shipping_price(order),
            "email": order.email,
            "id": order.id,
        }
    }


def cache_paid_order(order: Order) -> None:
    """Serialize and store a paid order in Redis.

    Called by pay_order() immediately after DB persist so that subsequent
    GET /order/<id> requests are served from Redis without hitting Postgres.
    Silent on any Redis error — the HTTP response must not be affected.
    """
    client = _get_redis_client(_redis_url())
    if client is None:
        return
    try:
        client.set(
            f"{_REDIS_KEY_PREFIX}{order.id}",
            json.dumps(order_to_dict(order)),
        )
    except Exception:
        pass
