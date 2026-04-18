from inf349.clients.products import ProductsClientError
from inf349.models import Product
from inf349.services.products import (
    bootstrap_products,
    list_products,
    product_to_dict,
    save_products,
    seed_products_if_empty,
)


SAMPLE = [
    {"id": 1, "name": "Eggs", "price": 28.1, "weight": 400, "in_stock": True},
    {"id": 2, "name": "Milk", "price": 10.5, "weight": 1000, "in_stock": False},
]


def test_save_products_inserts_new_records(db):
    count = save_products(SAMPLE)
    assert count == 2
    assert Product.select().count() == 2
    assert Product.get_by_id(1).name == "Eggs"


def test_save_products_is_idempotent(db):
    save_products(SAMPLE)
    count_second = save_products(SAMPLE)
    assert count_second == 0
    assert Product.select().count() == 2


def test_save_products_skips_incomplete_entries(db):
    bad = [{"id": 1}, {"name": "no id", "price": 1.0}, "not a dict"]
    count = save_products(bad)
    assert count == 0
    assert Product.select().count() == 0


def test_seed_products_if_empty_populates(db):
    count = seed_products_if_empty("http://ignored/", fetcher=lambda _: SAMPLE)
    assert count == 2
    assert Product.select().count() == 2


def test_seed_products_if_empty_is_noop_when_populated(db):
    Product.create(id=99, name="Seed guard", price=1.0)

    called = []

    def _fake_fetcher(url):
        called.append(url)
        return SAMPLE

    count = seed_products_if_empty("http://ignored/", fetcher=_fake_fetcher)
    assert count == 0
    assert called == []


def test_seed_products_swallows_client_error(db):
    def _broken(_):
        raise ProductsClientError("down")

    count = seed_products_if_empty("http://ignored/", fetcher=_broken)
    assert count == 0
    assert Product.select().count() == 0


def test_bootstrap_products_noop_when_table_missing(app):
    from inf349.db import database_proxy

    db = database_proxy.obj
    if db.is_closed():
        db.connect(reuse_if_open=True)
    count = bootstrap_products("http://ignored/")
    assert count == 0


def test_product_to_dict_has_expected_keys(db):
    product = Product.create(
        id=1,
        name="Brown eggs",
        type="dairy",
        price=28.1,
        weight=400,
        in_stock=True,
    )
    data = product_to_dict(product)
    assert set(data.keys()) == {
        "id", "name", "type", "description", "image",
        "height", "weight", "price", "rating", "in_stock",
    }
    assert data["id"] == 1
    assert data["in_stock"] is True


def test_list_products_returns_dicts_ordered_by_id(db):
    Product.create(id=2, name="B", price=2.0)
    Product.create(id=1, name="A", price=1.0)
    Product.create(id=3, name="C", price=3.0, in_stock=False)

    result = list_products()
    assert [p["id"] for p in result] == [1, 2, 3]
    assert result[2]["in_stock"] is False
