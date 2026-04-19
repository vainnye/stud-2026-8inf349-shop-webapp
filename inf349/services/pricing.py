from typing import Dict, Optional

from ..models import Order


TAX_RATES = {
    "QC": 0.15,
    "ON": 0.13,
    "AB": 0.05,
    "BC": 0.12,
    "NS": 0.14,
}


def compute_total_weight(order: Order) -> int:
    return sum((item.product.weight or 0) * item.quantity for item in order.items)


def compute_total_price(order: Order) -> float:
    total = sum(item.product.price * item.quantity for item in order.items)
    return round(total, 2)


def compute_shipping_price(order: Order) -> int:
    weight = compute_total_weight(order)
    if weight <= 500:
        return 5
    if weight < 2000:
        return 10
    return 25


def compute_tax_rate(shipping_information: Optional[Dict]) -> float:
    if not isinstance(shipping_information, dict):
        return 0
    province = shipping_information.get("province")
    return TAX_RATES.get(province, 0)


def compute_total_price_tax(order: Order) -> float:
    total = compute_total_price(order)
    rate = compute_tax_rate(order.shipping_information)
    return round(total * (1 + rate), 2)
