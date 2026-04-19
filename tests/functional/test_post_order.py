from inf349.models import Order, OrderProduct, Product


def _make_product(pid=1, in_stock=True):
    return Product.create(
        id=pid,
        name="Brown eggs",
        price=10.0,
        weight=400,
        in_stock=in_stock,
    )


def test_post_order_success_returns_302(client, db):
    _make_product()
    response = client.post("/order", json={"product": {"id": 1, "quantity": 2}})
    assert response.status_code == 302

    order = Order.get()
    assert response.headers["Location"].endswith(f"/order/{order.id}")

    items = list(order.items)
    assert len(items) == 1
    assert items[0].product_id == 1
    assert items[0].quantity == 2


def test_post_order_missing_body(client, db):
    response = client.post("/order", json={})
    assert response.status_code == 422
    body = response.get_json()
    assert body == {
        "errors": {
            "product": {
                "code": "missing-fields",
                "name": "La création d'une commande nécessite un produit",
            }
        }
    }


def test_post_order_missing_product_key(client, db):
    response = client.post("/order", json={"foo": "bar"})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_missing_id(client, db):
    response = client.post("/order", json={"product": {"quantity": 1}})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_missing_quantity(client, db):
    _make_product()
    response = client.post("/order", json={"product": {"id": 1}})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_quantity_zero(client, db):
    _make_product()
    response = client.post("/order", json={"product": {"id": 1, "quantity": 0}})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_quantity_negative(client, db):
    _make_product()
    response = client.post("/order", json={"product": {"id": 1, "quantity": -1}})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_unknown_product(client, db):
    response = client.post("/order", json={"product": {"id": 999, "quantity": 1}})
    assert response.status_code == 422
    assert response.get_json()["errors"]["product"]["code"] == "missing-fields"


def test_post_order_out_of_inventory(client, db):
    _make_product(in_stock=False)
    response = client.post("/order", json={"product": {"id": 1, "quantity": 1}})
    assert response.status_code == 422
    body = response.get_json()
    assert body["errors"]["product"]["code"] == "out-of-inventory"
    assert "inventaire" in body["errors"]["product"]["name"]


def test_post_order_creates_only_one_orderproduct(client, db):
    _make_product()
    client.post("/order", json={"product": {"id": 1, "quantity": 5}})
    assert OrderProduct.select().count() == 1


def test_post_order_does_not_persist_on_invalid_payload(client, db):
    _make_product(in_stock=False)
    client.post("/order", json={"product": {"id": 1, "quantity": 1}})
    assert Order.select().count() == 0
    assert OrderProduct.select().count() == 0
