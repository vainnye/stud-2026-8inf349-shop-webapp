import pytest

from inf349.models import Order, OrderProduct, Product
from inf349.services.orders import (
    OrderNotFoundError,
    OrderValidationError,
    create_order,
    update_client_info,
)


VALID_SHIPPING = {
    "country": "Canada",
    "address": "125 rue Gagnon",
    "postal_code": "G7X 3Y5",
    "city": "Chicoutimi",
    "province": "QC",
}


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


def _seed_order(db):
    _make_product()
    return create_order({"product": {"id": 1, "quantity": 2}})


def test_update_client_info_unknown_order_raises(db):
    with pytest.raises(OrderNotFoundError):
        update_client_info(999, {
            "order": {
                "email": "a@b.com",
                "shipping_information": VALID_SHIPPING,
            }
        })


def test_update_client_info_persists_email_and_shipping(db):
    order = _seed_order(db)

    updated = update_client_info(order.id, {
        "order": {
            "email": "jdoe@example.com",
            "shipping_information": VALID_SHIPPING,
        }
    })

    assert updated.email == "jdoe@example.com"
    assert updated.shipping_information == VALID_SHIPPING

    reloaded = Order.get_by_id(order.id)
    assert reloaded.email == "jdoe@example.com"
    assert reloaded.shipping_information == VALID_SHIPPING


def test_update_client_info_missing_order_wrapper_raises(db):
    order = _seed_order(db)
    with pytest.raises(OrderValidationError) as exc:
        update_client_info(order.id, {})
    assert exc.value.code == "missing-fields"
    assert exc.value.field == "order"
    assert exc.value.name == "Il manque un ou plusieurs champs qui sont obligatoires"


def test_update_client_info_missing_email_raises(db):
    order = _seed_order(db)
    with pytest.raises(OrderValidationError) as exc:
        update_client_info(order.id, {
            "order": {"shipping_information": VALID_SHIPPING}
        })
    assert exc.value.code == "missing-fields"
    assert exc.value.field == "order"


def test_update_client_info_empty_email_raises(db):
    order = _seed_order(db)
    with pytest.raises(OrderValidationError):
        update_client_info(order.id, {
            "order": {"email": "   ", "shipping_information": VALID_SHIPPING}
        })


def test_update_client_info_missing_shipping_raises(db):
    order = _seed_order(db)
    with pytest.raises(OrderValidationError):
        update_client_info(order.id, {
            "order": {"email": "a@b.com"}
        })


def test_update_client_info_partial_shipping_raises(db):
    order = _seed_order(db)
    partial = dict(VALID_SHIPPING)
    partial.pop("province")
    with pytest.raises(OrderValidationError) as exc:
        update_client_info(order.id, {
            "order": {"email": "a@b.com", "shipping_information": partial}
        })
    assert exc.value.code == "missing-fields"


def test_update_client_info_empty_shipping_field_raises(db):
    order = _seed_order(db)
    partial = dict(VALID_SHIPPING)
    partial["city"] = ""
    with pytest.raises(OrderValidationError):
        update_client_info(order.id, {
            "order": {"email": "a@b.com", "shipping_information": partial}
        })


def test_update_client_info_ignores_forbidden_fields(db):
    order = _seed_order(db)
    update_client_info(order.id, {
        "order": {
            "email": "a@b.com",
            "shipping_information": VALID_SHIPPING,
            "paid": True,
            "total_price": 9999,
            "id": 42,
            "transaction": {"hacked": True},
            "product": {"id": 2, "quantity": 999},
        }
    })

    reloaded = Order.get_by_id(order.id)
    assert reloaded.paid is False
    assert reloaded.transaction is None
    assert reloaded.id == order.id
    items = list(reloaded.items)
    assert len(items) == 1
    assert items[0].product_id == 1
    assert items[0].quantity == 2
