"""
Api endpoints
"""

from dataclasses import dataclass
from enum import StrEnum, auto
from logging import getLogger
from pathlib import Path
from statistics import quantiles

from flask import Blueprint, current_app, request
from peewee import DoesNotExist, IntegrityError

from shop_webapp.model import Order, OrderProduct, Product, db
from shop_webapp.util import validate_schema

log = getLogger(__name__)

api = Blueprint("api", __name__)

API_URL_PREFIX = "/api/"


# à noter que le prof a mentionné l'endpoint "/" dans son pdf
# j'assume qu'il voulait parler de l'endpoint "/products/"
@api.get("/products/")
def get_products():
    """Get a list of all products."""
    # selecting only the fields required by the api specs
    products = Product.select(
        Product.name,
        Product.id,
        Product.in_stock,
        Product.description,
        Product.price,
        Product.weight,
        Product.image,
    )
    current_app.logger.debug(f"listed {products.count()} products")
    return {"products": list(products.dicts())}


@db.atomic()
def place_order_for_product(product, quantity):
    order = Order.create()
    OrderProduct.create(order=order, product=product, quantity=quantity)
    return order


@api.post("/order/")
def post_order():
    """Post an order."""
    json_payload = request.get_json()
    current_app.logger.debug(f"received order: {json_payload}")

    schema = {"product": {"id": int, "quantity": int}}

    try:
        validate_schema(json_payload, schema)
        product = Product.get_by_id(json_payload["product"]["id"])
    except (TypeError, KeyError, DoesNotExist) as err:
        current_app.logger.debug(err)
        return (
            {
                "errors": {
                    "product": {
                        "code": "missing-fields",
                        "name": "La création d'une commande nécessite un produit",
                    }
                }
            },
            422,  # HTTP_422 Unprocessable Entity
        )

    if not product.in_stock:
        return (
            {
                "errors": {
                    "product": {
                        "code": "out-of-inventory",
                        "name": "Le produit demandé n'est pas en inventaire",
                    }
                }
            },
            422,  # HTTP_422 Unprocessable Entity
        )

    try:
        order = place_order_for_product(product, json_payload["product"]["quantity"])
    except Exception as err:
        current_app.logger.debug(err)
        return (
            "",
            500,  # HTTP_5XX Server error
        )
    return (
        "",
        302,  # HTTP_302 Found
        {"Location": f"{API_URL_PREFIX}order/{order.id}"},
    )
