from inf349.models import Order, OrderProduct, Product


VALID_SHIPPING = {
    "country": "Canada",
    "address": "125 rue Gagnon",
    "postal_code": "G7X 3Y5",
    "city": "Chicoutimi",
    "province": "QC",
}


ORDER_KEYS = {
    "shipping_information", "credit_card", "paid", "transaction",
    "product", "total_price", "total_price_tax", "shipping_price",
    "email", "id",
}


def _seed_order(weight=400, price=10.0, quantity=2):
    p = Product.create(
        id=1, name="Brown eggs", price=price, weight=weight, in_stock=True,
    )
    order = Order.create()
    OrderProduct.create(order=order, product=p, quantity=quantity)
    return order


def test_put_order_404_when_order_missing(client, db):
    response = client.put("/order/999", json={
        "order": {"email": "a@b.com", "shipping_information": VALID_SHIPPING}
    })
    assert response.status_code == 404


def test_put_order_success_returns_full_order(client, db):
    order = _seed_order(weight=400, price=10.0, quantity=2)

    response = client.put(f"/order/{order.id}", json={
        "order": {
            "email": "jdoe@example.com",
            "shipping_information": VALID_SHIPPING,
        }
    })

    assert response.status_code == 200
    body = response.get_json()
    assert set(body["order"].keys()) == ORDER_KEYS

    o = body["order"]
    assert o["email"] == "jdoe@example.com"
    assert o["shipping_information"] == VALID_SHIPPING
    assert o["credit_card"] == {}
    assert o["transaction"] == {}
    assert o["paid"] is False
    # tax applied now that province is known (QC 15%)
    assert o["total_price"] == 20.0
    assert o["total_price_tax"] == 23.0
    # weight = 400g * 2 = 800g → palier 500 < w < 2000 → 10$
    assert o["shipping_price"] == 10


def test_put_order_missing_order_wrapper_returns_422(client, db):
    order = _seed_order()
    response = client.put(f"/order/{order.id}", json={})
    assert response.status_code == 422
    assert response.get_json() == {
        "errors": {
            "order": {
                "code": "missing-fields",
                "name": "Il manque un ou plusieurs champs qui sont obligatoires",
            }
        }
    }


def test_put_order_missing_email(client, db):
    order = _seed_order()
    response = client.put(f"/order/{order.id}", json={
        "order": {"shipping_information": VALID_SHIPPING}
    })
    assert response.status_code == 422
    assert response.get_json()["errors"]["order"]["code"] == "missing-fields"


def test_put_order_missing_shipping_information(client, db):
    order = _seed_order()
    response = client.put(f"/order/{order.id}", json={
        "order": {"email": "a@b.com"}
    })
    assert response.status_code == 422
    assert response.get_json()["errors"]["order"]["code"] == "missing-fields"


def test_put_order_missing_any_shipping_field(client, db):
    order = _seed_order()
    for missing in ("country", "address", "postal_code", "city", "province"):
        shipping = dict(VALID_SHIPPING)
        shipping.pop(missing)
        response = client.put(f"/order/{order.id}", json={
            "order": {"email": "a@b.com", "shipping_information": shipping}
        })
        assert response.status_code == 422, f"expected 422 when {missing} missing"
        body = response.get_json()
        assert body["errors"]["order"]["code"] == "missing-fields"


def test_put_order_ignores_forbidden_fields(client, db):
    order = _seed_order()
    response = client.put(f"/order/{order.id}", json={
        "order": {
            "email": "a@b.com",
            "shipping_information": VALID_SHIPPING,
            "paid": True,
            "total_price": 9999,
            "total_price_tax": 9999,
            "shipping_price": 9999,
            "transaction": {"hacked": True},
            "id": 42,
            "product": {"id": 99, "quantity": 99},
        }
    })

    assert response.status_code == 200
    o = response.get_json()["order"]
    assert o["paid"] is False
    assert o["transaction"] == {}
    assert o["id"] == order.id
    assert o["product"] == {"id": 1, "quantity": 2}
    # shipping_price stays derived from weight (800g → 10$), not forced to 9999
    assert o["shipping_price"] == 10


def test_put_order_then_get_returns_updated_info(client, db):
    order = _seed_order()
    client.put(f"/order/{order.id}", json={
        "order": {"email": "a@b.com", "shipping_information": VALID_SHIPPING}
    })

    response = client.get(f"/order/{order.id}")
    assert response.status_code == 200
    o = response.get_json()["order"]
    assert o["email"] == "a@b.com"
    assert o["shipping_information"] == VALID_SHIPPING
