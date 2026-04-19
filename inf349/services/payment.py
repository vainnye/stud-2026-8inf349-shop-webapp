from typing import Callable, Dict, Optional

from ..db import database_proxy
from ..models import Order
from .orders import (
    OrderNotFoundError,
    OrderValidationError,
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

    return order
