from typing import Callable, Dict, Optional

from ..db import database_proxy
from ..models import Order
from .orders import (
    OrderNotFoundError,
    OrderValidationError,
    cache_paid_order,
    get_order,
)
from .pricing import compute_shipping_price, compute_total_price


_ALREADY_PAID = (
    "already-paid",
    "La commande a déjà été payée.",
)
_CLIENT_INFO_REQUIRED = (
    "missing-fields",
    "Les informations du client sont nécessaire avant d'appliquer une carte de crédit",
)
_MISSING_CARD_FIELDS = (
    "missing-fields",
    "Il manque un ou plusieurs champs qui sont obligatoires",
)
_INVALID_PAYMENT_RESPONSE = (
    "payment-error",
    "Réponse invalide du service de paiement",
)

# Redis key prefix for the transient "payment in progress" flag.
_PAYING_PREFIX = "paying:"
_PAYING_TTL = 300  # seconds — auto-expires if the worker crashes


# ---------------------------------------------------------------------------
# Redis helpers (paying flag)
# ---------------------------------------------------------------------------

def _make_redis_conn(redis_url: Optional[str]):
    """Return a Redis connection for redis_url, or None if unavailable."""
    if not redis_url:
        return None
    try:
        import redis as _redis
        return _redis.from_url(redis_url, decode_responses=True)
    except Exception:
        return None


def is_order_paying(order_id: int, redis_url: Optional[str]) -> bool:
    """Return True if a payment task for this order is currently in progress."""
    conn = _make_redis_conn(redis_url)
    if conn is None:
        return False
    try:
        return bool(conn.exists(f"{_PAYING_PREFIX}{order_id}"))
    except Exception:
        return False


def _set_order_paying(order_id: int, redis_url: Optional[str]) -> None:
    conn = _make_redis_conn(redis_url)
    if conn is None:
        return
    try:
        conn.set(f"{_PAYING_PREFIX}{order_id}", "1", ex=_PAYING_TTL)
    except Exception:
        pass


def _clear_order_paying(order_id: int, redis_url: Optional[str]) -> None:
    conn = _make_redis_conn(redis_url)
    if conn is None:
        return
    try:
        conn.delete(f"{_PAYING_PREFIX}{order_id}")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _persist_payment_failure(order: Order, amount_charged: float,
                              error: Dict) -> None:
    """Persist a payment error into order.transaction (partie 2 format).

    Called by process_payment for both network errors and remote declines.
    The order remains unpaid; credit_card stays empty.
    """
    with database_proxy.atomic():
        order.transaction = {
            "success": False,
            "error": error,
            "amount_charged": amount_charged,
        }
        order.save()


REQUIRED_CREDIT_CARD_FIELDS = (
    "name",
    "number",
    "expiration_year",
    "cvv",
    "expiration_month",
)


def _raise_order(info):
    code, name = info
    raise OrderValidationError(code, name, field="order")


def _raise_card(info):
    code, name = info
    raise OrderValidationError(code, name, field="credit_card")


def _validate_credit_card(raw):
    """Return a sanitized credit_card dict or None if invalid."""
    if not isinstance(raw, dict):
        return None
    cleaned = {}
    for key in REQUIRED_CREDIT_CARD_FIELDS:
        if key not in raw:
            return None
        value = raw[key]
        if key in ("expiration_year", "expiration_month"):
            if not isinstance(value, int) or isinstance(value, bool):
                return None
        else:
            if not isinstance(value, str) or value.strip() == "":
                return None
        cleaned[key] = value
    return cleaned


def _cache_order_with_url(order, redis_url: Optional[str]) -> None:
    """Cache a paid order using an explicit Redis URL (no Flask context needed).

    Used by process_payment() which runs inside an RQ worker where
    current_app is not available.
    """
    import json
    from .orders import order_to_dict

    conn = _make_redis_conn(redis_url)
    if conn is None:
        return
    try:
        conn.set(f"order:{order.id}", json.dumps(order_to_dict(order)))
    except Exception:
        pass


def _default_charger(payment_url: Optional[str]) -> Callable:
    """Build a charger bound to the configured remote URL."""
    from ..clients.payment import charge

    def _call(amount_charged: float, credit_card: Dict) -> Dict:
        return charge(amount_charged, credit_card, url=payment_url)

    return _call


def pay_order(order_id: int, payload: Dict,
              charger: Optional[Callable] = None,
              payment_url: Optional[str] = None) -> Order:
    """Apply a payment to an existing order.

    Raises OrderNotFoundError if the order id does not exist.
    Raises OrderValidationError (422 via the route) for:
      - already-paid order
      - order missing email / shipping_information
      - conflicting payload mixing credit_card with order info
      - malformed credit_card payload
      - any structured error returned by the remote payment service

    On success, persists masked credit_card + transaction and paid=True.
    """
    order = get_order(order_id)

    if order.paid:
        _raise_order(_ALREADY_PAID)

    if not order.email or not order.shipping_information:
        _raise_order(_CLIENT_INFO_REQUIRED)

    if not isinstance(payload, dict):
        _raise_card(_MISSING_CARD_FIELDS)

    # credit_card cannot be sent together with client info on the same PUT
    if "order" in payload:
        _raise_card(_MISSING_CARD_FIELDS)

    credit_card = _validate_credit_card(payload.get("credit_card"))
    if credit_card is None:
        _raise_card(_MISSING_CARD_FIELDS)

    # Per PDF example (p.10): amount_charged = total_price + shipping_price.
    # Taxes are NOT included in the charge sent to the remote payment service.
    amount_charged = round(
        compute_total_price(order) + compute_shipping_price(order), 2
    )

    if charger is None:
        charger = _default_charger(payment_url)

    # Network / transport errors bubble up as PaymentClientError; we relay
    # them as a credit_card validation error so the route returns 422 with
    # the standard errors shape.
    from ..clients.payment import PaymentClientError
    try:
        response = charger(amount_charged, credit_card)
    except PaymentClientError as err:
        raise OrderValidationError(err.code, err.name, field="credit_card") from err

    if not isinstance(response, dict):
        _raise_card(_INVALID_PAYMENT_RESPONSE)

    # Remote encodes declines / invalid data as:
    #   {"credit_card": {"code": "...", "name": "..."}}
    remote_cc = response.get("credit_card")
    if isinstance(remote_cc, dict) and "code" in remote_cc and "name" in remote_cc:
        # Relay verbatim. The HTTP layer must emit this error without the
        # `errors` wrapper to match the PDF example (page 10).
        raise OrderValidationError(
            remote_cc["code"], remote_cc["name"],
            field="credit_card", remote_relay=True,
        )

    transaction = response.get("transaction")
    if not isinstance(remote_cc, dict) or not isinstance(transaction, dict):
        _raise_card(_INVALID_PAYMENT_RESPONSE)

    with database_proxy.atomic():
        order.credit_card = remote_cc
        order.transaction = transaction
        order.paid = True
        order.save()

    # Persist to Redis immediately after DB commit so GET /order/<id>
    # can be served from cache without touching PostgreSQL.
    cache_paid_order(order)

    return order


# ---------------------------------------------------------------------------
# RQ background task
# ---------------------------------------------------------------------------

def process_payment(order_id: int, credit_card: Dict,
                    payment_url: Optional[str],
                    redis_url: Optional[str]) -> None:
    """RQ task: charge the card and persist the result.

    Runs inside an RQ worker (no Flask app context). All configuration is
    passed explicitly. On any outcome (success or failure) the "paying" flag
    is cleared and the result is written to the DB.
    """
    from ..models import Order
    from ..clients.payment import charge, PaymentClientError

    # Workers are forked processes — make sure the DB connection is open.
    try:
        database_proxy.obj.connect(reuse_if_open=True)
    except Exception:
        pass

    order = Order.get_by_id(order_id)
    amount_charged = round(
        compute_total_price(order) + compute_shipping_price(order), 2
    )

    try:
        # --- charge ---
        try:
            response = charge(amount_charged, credit_card, url=payment_url)
        except PaymentClientError as err:
            _persist_payment_failure(
                order, amount_charged,
                {"code": err.code, "name": err.name},
            )
            return

        if not isinstance(response, dict):
            _persist_payment_failure(
                order, amount_charged,
                {"code": "payment-error",
                 "name": "Réponse invalide du service de paiement"},
            )
            return

        remote_cc = response.get("credit_card")

        # The remote encodes errors in two possible shapes:
        #   1. {"credit_card": {"code": "...", "name": "..."}}   ← PDF example
        #   2. {"errors": {"credit_card": {"code": "...", "name": "..."}}}  ← actual UQAC service
        # Normalise: if direct key is missing or not an error dict, check errors.
        if not isinstance(remote_cc, dict) or "code" not in remote_cc:
            errors_block = response.get("errors")
            if isinstance(errors_block, dict):
                cc_err = errors_block.get("credit_card")
                if isinstance(cc_err, dict) and "code" in cc_err:
                    remote_cc = cc_err  # treat as a direct error dict

        if isinstance(remote_cc, dict) and "code" in remote_cc and "name" in remote_cc:
            _persist_payment_failure(
                order, amount_charged,
                {"code": remote_cc["code"], "name": remote_cc["name"]},
            )
            return

        transaction = response.get("transaction")
        if not isinstance(remote_cc, dict) or not isinstance(transaction, dict):
            _persist_payment_failure(
                order, amount_charged,
                {"code": "payment-error",
                 "name": "Réponse invalide du service de paiement"},
            )
            return

        # --- success ---
        with database_proxy.atomic():
            order.credit_card = remote_cc
            order.transaction = transaction
            order.paid = True
            order.save()

        _cache_order_with_url(order, redis_url)

    finally:
        _clear_order_paying(order_id, redis_url)


def enqueue_payment(order_id: int, payload: Dict,
                    payment_url: Optional[str],
                    redis_url: Optional[str]) -> None:
    """Validate synchronously then enqueue (or run inline) the payment task.

    Raises OrderNotFoundError / OrderValidationError for any validation
    problem — the route will translate these to 404 / 422 as usual.

    On validation success, either:
    - enqueues an RQ job (when Redis is configured), or
    - calls process_payment() synchronously (TESTING / no Redis).

    Returns None in both cases — the route always responds 202.
    """
    from .orders import get_order

    order = get_order(order_id)

    if order.paid:
        _raise_order(_ALREADY_PAID)

    if not order.email or not order.shipping_information:
        _raise_order(_CLIENT_INFO_REQUIRED)

    if not isinstance(payload, dict) or "order" in payload:
        _raise_card(_MISSING_CARD_FIELDS)

    credit_card = _validate_credit_card(payload.get("credit_card"))
    if credit_card is None:
        _raise_card(_MISSING_CARD_FIELDS)

    if redis_url is None:
        # No Redis (e.g. TESTING): run synchronously so the DB is updated
        # before the 202 response is sent. Keeps functional tests simple.
        process_payment(order_id, credit_card, payment_url, redis_url)
        return

    # Production path: set the paying flag, then push to the RQ default queue.
    _set_order_paying(order_id, redis_url)
    try:
        from rq import Queue
        conn = _make_redis_conn(redis_url)
        q = Queue(connection=conn)
        q.enqueue(process_payment, order_id, credit_card, payment_url, redis_url)
    except Exception:
        _clear_order_paying(order_id, redis_url)
        raise
