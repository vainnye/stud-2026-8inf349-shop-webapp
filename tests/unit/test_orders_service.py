import pytest

from inf349.models import Order, Product
from inf349.services.orders import OrderValidationError, create_order


def _make_product(pid=1, in_stock=True):
    return Product.create(
        id=pid,
        name="Brown eggs",
        price=10.0,
        weight=400,
        in_stock=in_stock,
    )


def test_create_order_persists_order_and_line(db):
    _make_product()
    order = create_order({"product": {"id": 1, "quantity": 3}})
    assert Order.select().count() == 1
    items = list(order.items)
    assert len(items) == 1
    assert items[0].product_id == 1
    assert items[0].quantity == 3


def test_create_order_missing_body_raises(db):
    with pytest.raises(OrderValidationError) as exc:
        create_order({})
    assert exc.value.code == "missing-fields"
    assert exc.value.field == "product"


def test_create_order_missing_product_key_raises(db):
    with pytest.raises(OrderValidationError) as exc:
        create_order({"foo": "bar"})
    assert exc.value.code == "missing-fields"


def test_create_order_missing_id_raises(db):
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"quantity": 1}})
    assert exc.value.code == "missing-fields"


def test_create_order_missing_quantity_raises(db):
    _make_product()
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"id": 1}})
    assert exc.value.code == "missing-fields"


def test_create_order_zero_quantity_raises(db):
    _make_product()
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"id": 1, "quantity": 0}})
    assert exc.value.code == "missing-fields"


def test_create_order_negative_quantity_raises(db):
    _make_product()
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"id": 1, "quantity": -2}})
    assert exc.value.code == "missing-fields"


def test_create_order_unknown_product_raises(db):
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"id": 999, "quantity": 1}})
    assert exc.value.code == "missing-fields"


def test_create_order_out_of_stock_raises(db):
    _make_product(in_stock=False)
    with pytest.raises(OrderValidationError) as exc:
        create_order({"product": {"id": 1, "quantity": 1}})
    assert exc.value.code == "out-of-inventory"
    assert "inventaire" in exc.value.name
