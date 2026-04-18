from inf349.models import Product


PRODUCT_KEYS = {
    "name", "id", "in_stock", "description", "price", "weight", "image",
}


def test_get_products_returns_empty_list(client, db):
    response = client.get("/")
    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"products": []}


def test_get_products_returns_all_products(client, db):
    Product.create(
        id=1,
        name="Brown eggs",
        description="Raw organic brown eggs in a basket",
        image="0.jpg",
        weight=400,
        price=28.1,
        in_stock=True,
    )
    Product.create(
        id=2,
        name="Out of stock widget",
        price=10.0,
        weight=100,
        in_stock=False,
    )

    response = client.get("/")
    assert response.status_code == 200
    data = response.get_json()

    assert list(data.keys()) == ["products"]
    assert len(data["products"]) == 2

    first = data["products"][0]
    assert set(first.keys()) == PRODUCT_KEYS
    assert first["id"] == 1
    assert first["name"] == "Brown eggs"
    assert first["in_stock"] is True

    second = data["products"][1]
    assert second["id"] == 2
    assert second["in_stock"] is False


def test_get_products_does_not_call_remote(client, db, monkeypatch):
    def _fail(*args, **kwargs):
        raise RuntimeError("GET / must not reach the remote service")

    monkeypatch.setattr("inf349.clients.products.urlopen", _fail)

    response = client.get("/")
    assert response.status_code == 200
