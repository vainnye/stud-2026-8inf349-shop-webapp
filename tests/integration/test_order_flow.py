"""End-to-end integration test for the Partie 1 order flow.

Exercises the full scenario expected by the énoncé, hitting the real HTTP
layer (Flask test client), real routes, real services, real Peewee models
and a real SQLite in-memory DB. Only the remote payment HTTP call is
mocked — everything else runs exactly as it would in production.

Scenario covered:
    1. A product is present in the catalogue (seeded directly, since the
       remote catalogue is out of scope for the integration test).
    2. POST /order creates an order → redirects (302) to /order/<id>.
    3. GET /order/<id> returns the initial shape (email/shipping/paid
       empty, product + computed prices present).
    4. PUT /order/<id> with email + shipping_information fills the client
       info and the response now carries taxes + shipping.
    5. PUT /order/<id> with credit_card triggers the (mocked) remote call,
       persists the masked card + transaction and flips paid=True.
    6. A final GET /order/<id> reflects every change.
"""

from api8inf349.models import Product


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


ORDER_KEYS = {
    "shipping_information", "credit_card", "paid", "transaction",
    "products", "total_price", "total_price_tax", "shipping_price",
    "email", "id",
}


def test_full_order_flow_end_to_end(client, db, monkeypatch):
    # ---- 1. catalogue ---------------------------------------------------
    Product.create(
        id=1, name="Brown eggs", price=10.0, weight=400, in_stock=True,
    )

    # ---- 2. POST /order -------------------------------------------------
    post_resp = client.post("/order", json={
        "product": {"id": 1, "quantity": 2},
    })
    assert post_resp.status_code == 302
    location = post_resp.headers["Location"]
    assert location.startswith("/order/")
    order_id = int(location.rsplit("/", 1)[-1])

    # ---- 3. GET /order/<id> (initial shape) ----------------------------
    get_resp = client.get(f"/order/{order_id}")
    assert get_resp.status_code == 200
    payload = get_resp.get_json()
    assert set(payload["order"].keys()) == ORDER_KEYS
    initial = payload["order"]
    assert initial["id"] == order_id
    assert initial["email"] is None
    assert initial["paid"] is False
    assert initial["shipping_information"] == {}
    assert initial["credit_card"] == {}
    assert initial["transaction"] == {}
    assert initial["products"] == [{"id": 1, "quantity": 2}]
    assert initial["total_price"] == 20.0
    # no province yet → total_price_tax == total_price
    assert initial["total_price_tax"] == 20.0
    # weight = 400 * 2 = 800g → tier 500 < w < 2000 → 10$
    assert initial["shipping_price"] == 10

    # ---- 4. PUT /order/<id> with client info ---------------------------
    put_info = client.put(f"/order/{order_id}", json={
        "order": {"email": "jdoe@example.com",
                  "shipping_information": VALID_SHIPPING},
    })
    assert put_info.status_code == 200
    with_info = put_info.get_json()["order"]
    assert with_info["email"] == "jdoe@example.com"
    assert with_info["shipping_information"] == VALID_SHIPPING
    assert with_info["paid"] is False
    # QC 15% tax now applied
    assert with_info["total_price"] == 20.0
    assert with_info["total_price_tax"] == 23.0
    assert with_info["shipping_price"] == 10

    # ---- 5. PUT /order/<id> with credit_card (mocked remote) -----------
    captured = {}

    def fake_charge(amount_charged, credit_card, url, timeout=10):
        captured["amount"] = amount_charged
        captured["card"] = credit_card
        captured["url"] = url
        return {
            "credit_card": MASKED_CARD,
            "transaction": {
                "id": "tx_integration_1",
                "success": True,
                "amount_charged": amount_charged,
            },
        }

    from api8inf349.clients import payment as payment_client
    monkeypatch.setattr(payment_client, "charge", fake_charge)

    # In TESTING mode (REDIS_URL=None) the payment runs synchronously and
    # the route responds 202 immediately (task "queued").
    pay_resp = client.put(f"/order/{order_id}", json={"credit_card": VALID_CARD})
    assert pay_resp.status_code == 202
    # Per PDF p.10: amount = total_price + shipping_price (no tax)
    assert captured["amount"] == 30.0

    # ---- 6. Final GET reflects every mutation --------------------------
    final = client.get(f"/order/{order_id}").get_json()["order"]
    assert final["paid"] is True
    assert final["credit_card"] == MASKED_CARD
    assert final["transaction"]["id"] == "tx_integration_1"
    assert final["transaction"]["success"] is True
    assert final["transaction"]["amount_charged"] == 30.0
    assert final["email"] == "jdoe@example.com"
    assert final["shipping_information"] == VALID_SHIPPING
    assert final["total_price"] == 20.0
    assert final["total_price_tax"] == 23.0
    assert final["shipping_price"] == 10


def test_full_order_flow_declined_card_persisted_in_transaction(
    client, db, monkeypatch,
):
    """A declined card is persisted in transaction.error and the order stays
    unpaid (async path: PUT returns 202, error visible via GET)."""
    Product.create(
        id=1, name="Brown eggs", price=10.0, weight=400, in_stock=True,
    )

    post_resp = client.post("/order", json={"product": {"id": 1, "quantity": 2}})
    order_id = int(post_resp.headers["Location"].rsplit("/", 1)[-1])

    client.put(f"/order/{order_id}", json={
        "order": {"email": "jdoe@example.com",
                  "shipping_information": VALID_SHIPPING},
    })

    def fake_charge_declined(amount_charged, credit_card, url, timeout=10):
        return {
            "credit_card": {
                "code": "card-declined",
                "name": "La carte de crédit a été déclinée.",
            }
        }

    from api8inf349.clients import payment as payment_client
    monkeypatch.setattr(payment_client, "charge", fake_charge_declined)

    # In TESTING mode (REDIS_URL=None) the task runs synchronously; route
    # responds 202 once the (failed) charge is persisted.
    pay_resp = client.put(f"/order/{order_id}", json={"credit_card": VALID_CARD})
    assert pay_resp.status_code == 202

    # Error is stored in the transaction field; order remains unpaid.
    after = client.get(f"/order/{order_id}").get_json()["order"]
    assert after["paid"] is False
    assert after["credit_card"] == {}
    assert after["transaction"]["success"] is False
    assert after["transaction"]["error"]["code"] == "card-declined"
