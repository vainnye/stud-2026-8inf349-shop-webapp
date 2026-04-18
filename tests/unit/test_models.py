from inf349.models import Order, OrderProduct, Product, get_all_models


def test_all_models_registered():
    names = {m.__name__ for m in get_all_models()}
    assert names == {"Product", "Order", "OrderProduct"}


def test_create_product(db):
    Product.create(
        id=1,
        name="Brown eggs",
        price=28.1,
        weight=400,
        in_stock=True,
    )
    assert Product.get_by_id(1).name == "Brown eggs"


def test_order_supports_multiple_products(db):
    p1 = Product.create(id=1, name="A", price=10.0, weight=100)
    p2 = Product.create(id=2, name="B", price=20.0, weight=200)
    order = Order.create(email="test@example.com")
    OrderProduct.create(order=order, product=p1, quantity=2)
    OrderProduct.create(order=order, product=p2, quantity=1)

    items = list(order.items)
    assert len(items) == 2
    assert {i.product_id for i in items} == {1, 2}


def test_order_json_fields_roundtrip(db):
    order = Order.create(
        shipping_information={"country": "Canada", "postal_code": "G7H 2B1"},
        credit_card={"name": "John Doe", "number": "****4242"},
        transaction={"id": "abc", "success": True, "amount_charged": 49.99},
    )
    reloaded = Order.get_by_id(order.id)
    assert reloaded.shipping_information["country"] == "Canada"
    assert reloaded.credit_card["number"] == "****4242"
    assert reloaded.transaction["success"] is True


def test_order_defaults(db):
    order = Order.create()
    assert order.paid is False
    assert order.email is None
    assert order.shipping_information is None
    assert order.credit_card is None
    assert order.transaction is None
