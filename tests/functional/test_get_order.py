from inf349.models import Order, OrderProduct, Product


ORDER_KEYS = {
    "shipping_information", "credit_card", "paid", "transaction",
    "product", "total_price", "total_price_tax", "shipping_price",
    "email", "id",
}


def _seed_order(price=10.0, weight=400, quantity=2, pid=1):
    p = Product.create(
        id=pid, name="Brown eggs", price=price, weight=weight, in_stock=True,
    )
    order = Order.create()
    OrderProduct.create(order=order, product=p, quantity=quantity)
    return order


def test_get_order_404_when_not_found(client, db):
    response = client.get("/order/999")
    assert response.status_code == 404


def test_get_order_returns_expected_shape(client, db):
    order = _seed_order(price=10.0, weight=400, quantity=2)
    response = client.get(f"/order/{order.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert list(data.keys()) == ["order"]

    o = data["order"]
    assert set(o.keys()) == ORDER_KEYS

    assert o["id"] == order.id
    assert o["email"] is None
    assert o["paid"] is False
    assert o["shipping_information"] == {}
    assert o["credit_card"] == {}
    assert o["transaction"] == {}
    assert o["product"] == {"id": 1, "quantity": 2}
    assert o["total_price"] == 20.0
    assert o["shipping_price"] == 5
    assert o["total_price_tax"] == 20.0


def test_get_order_uses_singular_product_key(client, db):
    order = _seed_order()
    response = client.get(f"/order/{order.id}")
    o = response.get_json()["order"]
    assert "product" in o
    assert "products" not in o


def test_get_order_shipping_price_1kg(client, db):
    order = _seed_order(weight=1000, quantity=1)
    o = client.get(f"/order/{order.id}").get_json()["order"]
    assert o["shipping_price"] == 10


def test_get_order_shipping_price_3kg(client, db):
    order = _seed_order(weight=3000, quantity=1)
    o = client.get(f"/order/{order.id}").get_json()["order"]
    assert o["shipping_price"] == 25


def test_get_order_tax_applied_when_province_set(client, db):
    order = _seed_order(price=10.0, weight=400, quantity=2)
    order.shipping_information = {"province": "QC"}
    order.save()

    o = client.get(f"/order/{order.id}").get_json()["order"]
    assert o["total_price"] == 20.0
    assert o["total_price_tax"] == 23.0


def test_get_order_does_not_persist_calculations(client, db):
    order = _seed_order()
    client.get(f"/order/{order.id}")

    field_names = set(Order._meta.fields.keys())
    assert "total_price" not in field_names
    assert "total_price_tax" not in field_names
    assert "shipping_price" not in field_names


def test_get_order_non_integer_id_returns_404(client, db):
    response = client.get("/order/abc")
    assert response.status_code == 404
