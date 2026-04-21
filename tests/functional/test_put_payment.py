"""Functional tests for PUT /order/<id> with credit_card.

In TESTING mode (REDIS_URL=None) enqueue_payment() runs process_payment()
synchronously, so the DB is already updated when the 202 is returned. Tests
can therefore inspect the order state via a subsequent GET.
"""
from api8inf349.models import Order, OrderProduct, Product
from api8inf349.services.orders import update_client_info


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
    p = Product.create(
        id=1, name="Brown eggs", price=10.0, weight=400, in_stock=True,
    )
    order = Order.create()
    OrderProduct.create(order=order, product=p, quantity=2)
    update_client_info(order.id, {
        "order": {"email": "a@b.com", "shipping_information": VALID_SHIPPING}
    })
    return Order.get_by_id(order.id)


def _install_fake_charge(monkeypatch, fake):
    from api8inf349.clients import payment as payment_client
    monkeypatch.setattr(payment_client, "charge", fake)


def test_put_payment_404_on_unknown_order(client, db):
    response = client.put("/order/999", json={"credit_card": VALID_CARD})
    assert response.status_code == 404


def test_put_payment_success(client, db, monkeypatch):
    order = _seed_ready_order()

    def fake_charge(amount_charged, credit_card, url, timeout=10):
        return {
            "credit_card": MASKED_CARD,
            "transaction": {
                "id": "tx_1",
                "success": True,
                "amount_charged": amount_charged,
            },
        }

    _install_fake_charge(monkeypatch, fake_charge)

    # PUT enqueues (runs sync in TESTING) and returns 202 immediately.
    response = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert response.status_code == 202

    # Subsequent GET reflects the completed payment.
    get_resp = client.get(f"/order/{order.id}")
    assert get_resp.status_code == 200
    body = get_resp.get_json()["order"]
    assert body["paid"] is True
    assert body["credit_card"] == MASKED_CARD
    assert body["transaction"]["id"] == "tx_1"
    assert body["transaction"]["success"] is True
    # Per PDF (p.10): amount_charged = total_price + shipping_price, no tax.
    # total_price = 20 ; weight 800g → shipping 10 → charge 30
    assert body["transaction"]["amount_charged"] == 30.0


def test_put_payment_missing_client_info_returns_422(client, db, monkeypatch):
    p = Product.create(id=1, name="X", price=10.0, weight=100, in_stock=True)
    order = Order.create()
    OrderProduct.create(order=order, product=p, quantity=1)

    _install_fake_charge(monkeypatch, lambda *a, **k: {})

    response = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert response.status_code == 422
    assert response.get_json() == {
        "errors": {
            "order": {
                "code": "missing-fields",
                "name": (
                    "Les informations du client sont nécessaire avant "
                    "d'appliquer une carte de crédit"
                ),
            }
        }
    }


def test_put_payment_already_paid_returns_422(client, db, monkeypatch):
    order = _seed_ready_order()

    def fake_charge(amount_charged, credit_card, url, timeout=10):
        return {
            "credit_card": MASKED_CARD,
            "transaction": {"id": "tx_1", "success": True, "amount_charged": amount_charged},
        }

    _install_fake_charge(monkeypatch, fake_charge)

    first = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert first.status_code == 202

    second = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert second.status_code == 422
    assert second.get_json() == {
        "errors": {
            "order": {
                "code": "already-paid",
                "name": "La commande a déjà été payée.",
            }
        }
    }


def test_put_payment_declined_persisted_in_transaction(client, db, monkeypatch):
    """A declined card is persisted in transaction.error; order stays unpaid."""
    order = _seed_ready_order()

    def fake_charge_declined(amount_charged, credit_card, url, timeout=10):
        return {
            "credit_card": {
                "code": "card-declined",
                "name": "La carte de crédit a été déclinée.",
            }
        }

    _install_fake_charge(monkeypatch, fake_charge_declined)

    response = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert response.status_code == 202

    after = client.get(f"/order/{order.id}").get_json()["order"]
    assert after["paid"] is False
    assert after["credit_card"] == {}
    assert after["transaction"]["success"] is False
    assert after["transaction"]["error"]["code"] == "card-declined"


def test_put_payment_network_error_persisted_in_transaction(client, db, monkeypatch):
    """A network error is persisted in transaction.error; order stays unpaid."""
    from api8inf349.clients.payment import PaymentClientError

    order = _seed_ready_order()

    def fake_charge(amount_charged, credit_card, url, timeout=10):
        raise PaymentClientError(
            "payment-unreachable",
            "Le service de paiement est indisponible",
        )

    _install_fake_charge(monkeypatch, fake_charge)

    response = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert response.status_code == 202

    after = client.get(f"/order/{order.id}").get_json()["order"]
    assert after["paid"] is False
    assert after["transaction"]["success"] is False
    assert after["transaction"]["error"]["code"] == "payment-unreachable"


def test_put_payment_missing_fields_returns_422(client, db, monkeypatch):
    order = _seed_ready_order()
    _install_fake_charge(monkeypatch, lambda *a, **k: {})

    partial = dict(VALID_CARD)
    partial.pop("cvv")
    response = client.put(f"/order/{order.id}", json={"credit_card": partial})
    assert response.status_code == 422
    body = response.get_json()
    assert body["errors"]["credit_card"]["code"] == "missing-fields"


def test_put_payment_conflict_with_order_key_returns_422(client, db, monkeypatch):
    order = _seed_ready_order()
    _install_fake_charge(monkeypatch, lambda *a, **k: {})

    response = client.put(f"/order/{order.id}", json={
        "credit_card": VALID_CARD,
        "order": {"email": "x@y.com", "shipping_information": VALID_SHIPPING},
    })
    assert response.status_code == 422
    body = response.get_json()
    assert "credit_card" in body["errors"]


def test_put_payment_does_not_touch_client_info(client, db, monkeypatch):
    order = _seed_ready_order()

    def fake_charge(amount_charged, credit_card, url, timeout=10):
        return {
            "credit_card": MASKED_CARD,
            "transaction": {"id": "tx_1", "success": True, "amount_charged": amount_charged},
        }

    _install_fake_charge(monkeypatch, fake_charge)

    resp = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert resp.status_code == 202

    reloaded = Order.get_by_id(order.id)
    assert reloaded.email == "a@b.com"
    assert reloaded.shipping_information == VALID_SHIPPING


def test_put_payment_paying_flag_returns_409(client, db, monkeypatch):
    """While a payment is in progress (paying flag set), PUT returns 409."""
    order = _seed_ready_order()

    # Patch at the import site used by the route, not at the definition site.
    from api8inf349.routes import orders as orders_route
    monkeypatch.setattr(orders_route, "is_order_paying", lambda order_id, redis_url: True)

    response = client.put(f"/order/{order.id}", json={"credit_card": VALID_CARD})
    assert response.status_code == 409


def test_get_order_paying_flag_returns_202(client, db, monkeypatch):
    """While a payment is in progress (paying flag set), GET returns 202."""
    order = _seed_ready_order()

    from api8inf349.routes import orders as orders_route
    monkeypatch.setattr(orders_route, "is_order_paying", lambda order_id, redis_url: True)

    response = client.get(f"/order/{order.id}")
    assert response.status_code == 202
