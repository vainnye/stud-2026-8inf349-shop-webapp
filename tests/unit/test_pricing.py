from inf349.models import Order, OrderProduct, Product
from inf349.services.pricing import (
    compute_shipping_price,
    compute_tax_rate,
    compute_total_price,
    compute_total_price_tax,
    compute_total_weight,
)


def _make_order(weight, price, quantity, province=None, pid=1):
    p = Product.create(
        id=pid, name="X", price=price, weight=weight, in_stock=True,
    )
    order = Order.create()
    if province is not None:
        order.shipping_information = {"province": province}
        order.save()
    OrderProduct.create(order=order, product=p, quantity=quantity)
    return order


def test_total_weight(db):
    order = _make_order(weight=250, price=1.0, quantity=3)
    assert compute_total_weight(order) == 750


def test_total_price(db):
    order = _make_order(weight=100, price=12.5, quantity=4)
    assert compute_total_price(order) == 50.0


def test_shipping_price_under_500(db):
    order = _make_order(weight=100, price=1.0, quantity=1)
    assert compute_shipping_price(order) == 5


def test_shipping_price_exactly_500(db):
    order = _make_order(weight=500, price=1.0, quantity=1)
    assert compute_shipping_price(order) == 5


def test_shipping_price_between_500_and_2000(db):
    order = _make_order(weight=1000, price=1.0, quantity=1)
    assert compute_shipping_price(order) == 10


def test_shipping_price_exactly_2000(db):
    order = _make_order(weight=2000, price=1.0, quantity=1)
    assert compute_shipping_price(order) == 25


def test_shipping_price_above_2000(db):
    order = _make_order(weight=2500, price=1.0, quantity=1)
    assert compute_shipping_price(order) == 25


def test_shipping_price_cumulative_quantity(db):
    # 400g x 3 = 1200g → bucket 10
    order = _make_order(weight=400, price=1.0, quantity=3)
    assert compute_shipping_price(order) == 10


def test_tax_rate_each_province():
    assert compute_tax_rate({"province": "QC"}) == 0.15
    assert compute_tax_rate({"province": "ON"}) == 0.13
    assert compute_tax_rate({"province": "AB"}) == 0.05
    assert compute_tax_rate({"province": "BC"}) == 0.12
    assert compute_tax_rate({"province": "NS"}) == 0.14


def test_tax_rate_unknown_province():
    assert compute_tax_rate({"province": "ZZ"}) == 0


def test_tax_rate_empty_or_none():
    assert compute_tax_rate({}) == 0
    assert compute_tax_rate(None) == 0


def test_total_price_tax_without_province(db):
    order = _make_order(weight=100, price=10.0, quantity=2)
    assert compute_total_price_tax(order) == 20.0


def test_total_price_tax_qc(db):
    order = _make_order(weight=100, price=10.0, quantity=2, province="QC")
    assert compute_total_price_tax(order) == 23.0


def test_total_price_tax_ab(db):
    order = _make_order(weight=100, price=100.0, quantity=1, province="AB")
    assert compute_total_price_tax(order) == 105.0


def test_total_price_tax_rounding(db):
    order = _make_order(weight=100, price=19.99, quantity=1, province="QC")
    # 19.99 * 1.15 = 22.9885 → 22.99
    assert compute_total_price_tax(order) == 22.99
