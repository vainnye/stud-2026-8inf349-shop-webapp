"""
Api endpoints
"""

from flask import Blueprint, current_app, request
from peewee import DoesNotExist, IntegrityError
from playhouse.shortcuts import model_to_dict

from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
    db,
)
from shop_webapp.util import validate_schema

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
    order = Order.create(paid=False)
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


@api.get("/order/<int:id>")
def get_order_by_id(id: int):
    try:
        with db.atomic():  # transaction pour assurer l'intégrité des données
            order = Order.get_by_id(id)
            order_product = order.order_products.first()
            product = order_product.product
            transaction = (
                order.transactions.select(
                    Transaction.id,
                    Transaction.success,
                    Transaction.amount_charged,
                )
                .dicts()
                .first()
                or {}
            )
            credit_card = (
                order.credit_cards.select(
                    CreditCard.name,
                    CreditCard.number,
                    CreditCard.expiration_month,
                    CreditCard.expiration_year,
                    CreditCard.cvv,
                )
                .dicts()
                .first()
                or {}
            )
            shipping_information = (
                order.shipping_informations.select(
                    ShippingInformation.country,
                    ShippingInformation.province,
                    ShippingInformation.address,
                    ShippingInformation.city,
                    ShippingInformation.postal_code,
                )
                .dicts()
                .first()
                or {}
            )

        if not order.paid:
            # update the prices
            order.calc_total_price(product.price, order_product.quantity)
            if shipping_information and (
                province := shipping_information.get(ShippingInformation.province)
            ):
                order.calc_total_price_tax(order.total_price, province)
                order.calc_shipping_price(
                    order.total_price_tax, order.weight, order_product.quantity
                )
            order.save()

        response_order = model_to_dict(
            order,
            only=(
                Order.id,
                Order.email,
                Order.paid,
                Order.total_price,
                Order.total_price_tax,
                Order.shipping_price,
            ),
        )

        response_order["transaction"] = transaction
        response_order["shipping_information"] = shipping_information
        response_order["credit_card"] = credit_card
        response_order["product"] = {
            "id": product.id,
            "quantity": order_product.quantity,
        }

        return {"order": response_order}
    except DoesNotExist as err:
        current_app.logger.debug(f"{err!r}")
        return (
            "",
            404,  # HTTP_404 Not found
        )
    except Exception as err:
        current_app.logger.debug(f"{err!r}")
        return (
            "",
            500,  # HTTP_500 Internal Server Error
        )
