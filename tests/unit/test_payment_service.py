import pytest

from inf349.models import Order, Product
from inf349.services.orders import (
    OrderNotFoundError,
    OrderValidationError,
    create_order,
    update_client_info,
)
from inf349.services.payment import pay_order


VALID_SHIPPING = {
    "country": "Canada",
    "address": "125 rue Gagnon",
    "postal_code": "G7X 3Y5",
    "city": "Chicoutimi",
    "province": "QC",
}

VALID_CARD = {
    "name": "John Doe",
    "number": "4242424242424242",
    "expiration_year": 2024,
    "cvv": "123",
    "expiration_month": 9,
}

MASKED_CARD = {
    "name": "John Doe",
    "first_digits": "4242",
    "last_digits": "4242",
    "expiration_year": 2024,
    "expiration_month": 9,
}


def _seed_ready_order():
    Product.create(
        id=1, name="Brown eggs", price=10.0, weight=400, in_stock=True,
    )
    order = create_order({"product": {"id": 1, "quantity": 2}})
    update_client_info(order.id, {
        "order": {"email": "a@b.com", "shipping_information": VALID_SHIPPING}
    })
    return Order.get_by_id(order.id)


def _charger_success(amount_charged, credit_card):
    return {
        "credit_card": MASKED_CARD,
        "transaction": {
            "id": "tx_1",
            "success": True,
            "amount_charged": amount_charged,
        },
    }


def _charger_declined(amount_charged, credit_card):
    return {
        "credit_card": {
            "code": "card-declined",
            "name": "La carte de crédit a été déclinée.",
        }
    }


def test_pay_order_unknown_order_raises(db):
    with pytest.raises(OrderNotFoundError):
        pay_order(999, {"credit_card": VALID_CARD}, charger=_charger_success)


def test_pay_order_success_persists_transaction_and_masked_card(db):
    order = _seed_ready_order()
    updated = pay_order(
        order.id, {"credit_card": VALID_CARD}, charger=_charger_success,
    )
    assert updated.paid is True
    assert updated.credit_card == MASKED_CARD
    assert updated.transaction["id"] == "tx_1"

    reloaded = Order.get_by_id(order.id)
    assert reloaded.paid is True
    assert reloaded.credit_card == MASKED_CARD
    assert reloaded.transaction["success"] is True


def test_pay_order_amount_is_total_price_plus_shipping(db):
    order = _seed_ready_order()
    captured = {}

    def charger(amount_charged, credit_card):
        captured["amount"] = amount_charged
        return _charger_success(amount_charged, credit_card)

    pay_order(order.id, {"credit_card": VALID_CARD}, charger=charger)
    # Per PDF (p.10): amount_charged = total_price + shipping_price, no tax.
    # total_price = 20 ; weight 800g → shipping 10 → charge 30
    assert captured["amount"] == 30.0


def test_pay_order_already_paid_raises_with_422_code(db):
    order = _seed_ready_order()
    pay_order(order.id, {"credit_card": VALID_CARD}, charger=_charger_success)

    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {"credit_card": VALID_CARD}, charger=_charger_success)
    assert exc.value.code == "already-paid"
    assert exc.value.field == "order"
    assert exc.value.name == "La commande a déjà été payée."


def test_pay_order_without_client_info_raises(db):
    Product.create(id=1, name="X", price=10.0, weight=100, in_stock=True)
    order = create_order({"product": {"id": 1, "quantity": 1}})

    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {"credit_card": VALID_CARD}, charger=_charger_success)
    assert exc.value.code == "missing-fields"
    assert exc.value.field == "order"
    assert exc.value.name == (
        "Les informations du client sont nécessaire avant d'appliquer une carte de crédit"
    )


def test_pay_order_missing_credit_card_raises(db):
    order = _seed_ready_order()
    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {}, charger=_charger_success)
    assert exc.value.code == "missing-fields"
    assert exc.value.field == "credit_card"


def test_pay_order_incomplete_credit_card_raises(db):
    order = _seed_ready_order()
    for missing in ("name", "number", "expiration_year", "cvv", "expiration_month"):
        partial = dict(VALID_CARD)
        partial.pop(missing)
        with pytest.raises(OrderValidationError) as exc:
            pay_order(
                order.id, {"credit_card": partial}, charger=_charger_success,
            )
        assert exc.value.field == "credit_card", f"field check failed for {missing}"


def test_pay_order_empty_string_fields_raise(db):
    order = _seed_ready_order()
    partial = dict(VALID_CARD)
    partial["name"] = "   "
    with pytest.raises(OrderValidationError):
        pay_order(order.id, {"credit_card": partial}, charger=_charger_success)


def test_pay_order_non_int_expiration_raises(db):
    order = _seed_ready_order()
    partial = dict(VALID_CARD)
    partial["expiration_year"] = "2024"
    with pytest.raises(OrderValidationError):
        pay_order(order.id, {"credit_card": partial}, charger=_charger_success)


def test_pay_order_conflict_with_order_key_raises(db):
    order = _seed_ready_order()
    with pytest.raises(OrderValidationError) as exc:
        pay_order(
            order.id,
            {"credit_card": VALID_CARD, "order": {"email": "x@y.com"}},
            charger=_charger_success,
        )
    assert exc.value.field == "credit_card"


def test_pay_order_relays_remote_decline(db):
    order = _seed_ready_order()
    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {"credit_card": VALID_CARD}, charger=_charger_declined)
    assert exc.value.code == "card-declined"
    assert exc.value.field == "credit_card"
    assert exc.value.name == "La carte de crédit a été déclinée."

    reloaded = Order.get_by_id(order.id)
    assert reloaded.paid is False
    assert reloaded.transaction is None


def test_pay_order_network_error_raises_as_validation_error(db):
    from inf349.clients.payment import PaymentClientError

    order = _seed_ready_order()

    def broken_charger(amount_charged, credit_card):
        raise PaymentClientError(
            "payment-unreachable",
            "Le service de paiement est indisponible",
        )

    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {"credit_card": VALID_CARD}, charger=broken_charger)
    assert exc.value.code == "payment-unreachable"
    assert exc.value.field == "credit_card"

    reloaded = Order.get_by_id(order.id)
    assert reloaded.paid is False


def test_pay_order_invalid_remote_response_raises(db):
    order = _seed_ready_order()

    def bad_charger(amount_charged, credit_card):
        return {"unexpected": "shape"}

    with pytest.raises(OrderValidationError) as exc:
        pay_order(order.id, {"credit_card": VALID_CARD}, charger=bad_charger)
    assert exc.value.field == "credit_card"
