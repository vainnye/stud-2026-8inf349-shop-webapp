"""
Api endpoints
"""

from datetime import date
from enum import Enum
from json import JSONDecodeError

from flask import Blueprint, current_app, request
from peewee import DoesNotExist, IntegrityError
from playhouse.shortcuts import model_to_dict

from shop_webapp.globals import API_URL_PATH, THIRD_PARTY_PAYMENT_URL
from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
    db,
)
from shop_webapp.util import (
    ValidationError,
    ValidationMissingField,
    follows_schema,
    http_post,
    validate_schema,
)


class ApiException(Exception):
    def __init__(self, code: str, *args: object) -> None:
        super().__init__(*args)
        self.code = code or "default-error"
        self.on = "default-cause"
        self.msg = "falling back to default error (server error)"
        self.status = 500

    def __call__(self, status: int, on: str, msg: str):
        self.status = status
        self.on = on
        self.msg = msg
        return self

    def error(self):
        return {"errors": {self.on: {"code": self.code, "name": self.msg}}}, self.status


class Exc(ApiException, Enum):
    CardDeclined = "card-declined"
    ExpiredCard = "expired-card"
    ThirdParty = "third-party"
    MissingFields = "missing-fields"
    IncompatibleFields = "incompatible-fields"
    IncorrectValues = "incorrect-values"
    IncorrectNumber = "incorrect-number"  # credit card number


api = Blueprint("api", __name__)


# à noter que le prof a mentionné l'endpoint "/" dans son pdf
# j'assume qu'il voulait parler de l'endpoint "/products/"
# il ne faut pas mal identifier les ressources
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
        if json_payload["product"]["quantity"] < 1:
            raise ValidationMissingField()

        product = Product.get_by_id(json_payload["product"]["id"])
        if not product.in_stock:
            raise ApiException("out-of-inventory")(
                422, "product", "Le produit demandé n'est pas en inventaire"
            )
        order = place_order_for_product(product, json_payload["product"]["quantity"])
        return (
            "",
            302,  # HTTP_302 Found
            {"Location": f"{API_URL_PATH.as_posix()}/order/{order.id}"},
        )
    except ApiException as err:
        current_app.logger.debug(f"{err!r}")
        return err.error()
    except (DoesNotExist, ValidationError, IntegrityError) as err:
        current_app.logger.debug(err)
        return Exc.MissingFields(
            422, "product", "La création d'une commande nécessite un produit"
        ).error()
    except Exception as err:
        current_app.logger.debug(err)
        return (
            "",
            500,  # HTTP_5XX Server error
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
            current_app.logger.debug(f"order {order.id} not paid, updating prices")
            order.calc_total_price(product.price, order_product.quantity)
            if shipping_information and (
                province := shipping_information.get("province")
            ):
                current_app.logger.debug(
                    f"order {order.id} has shipping information, updating taxed price and shipping price"
                )
                order.calc_total_price_tax(order.total_price, province)
                order.calc_shipping_price(
                    order.total_price_tax, product.weight, order_product.quantity
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


@api.put("/order/<int:id>")
def update_order(id: int):
    json_payload = request.get_json()
    current_app.logger.debug(f"received order update: {json_payload!r}")

    try:
        client_info_schema = {
            "order": {
                "email": str,
                "shipping_information": {
                    "country": str,
                    "address": str,
                    "province": str,
                    "city": str,
                    "postal_code": str,
                },
            }
        }

        credit_card_info_schema = {
            "credit_card": {
                "name": str,
                "number": str,
                "expiration_year": int,
                "cvv": str,
                "expiration_month": int,
            },
        }
        if "credit_card" in json_payload and "order" in json_payload:
            raise Exc.IncompatibleFields(
                422,
                "order",
                "Les informations de la commande et la carte de crédit ne peuvent pas être renseignés en même temps",
            )

        if follows_schema(json_payload, client_info_schema):
            info = json_payload["order"]["shipping_information"]
            with db.atomic():
                order = Order.get_by_id(id)
                order.email = json_payload["order"]["email"]
                order.save()
                ShippingInformation.insert(
                    order=order,
                    country=info["country"],
                    address=info["address"],
                    province=info["province"],
                    city=info["city"],
                    postal_code=info["postal_code"],
                ).on_conflict_replace().execute()
            return get_order_by_id(order.id)
        elif follows_schema(json_payload, credit_card_info_schema):
            number = json_payload["credit_card"]["number"]
            if number not in ("4242 4242 4242 4242", "4000 0000 0000 0002"):
                raise Exc.IncorrectNumber(
                    422,
                    "credit_card",
                    "Seules les cartes de crédit de test sont acceptées '4242 4242 4242 4242' et '4000 0000 0000 0002'",
                )
            expiration_month = json_payload["credit_card"]["expiration_month"]
            expiration_year = json_payload["credit_card"]["expiration_year"]
            today = date.today()
            if (
                not (0 < expiration_month < 13)
                or expiration_year < today.year
                or (expiration_year == today.year and expiration_month < today.month)
            ):
                raise Exc.ExpiredCard(
                    422, "credit_card", "La carte de crédit est expirée"
                )
            cvv = json_payload["credit_card"]["cvv"]
            if len(cvv) != 3 or not cvv.isnumeric():
                return Exc.IncorrectValues(
                    422, "credit_card", "Le cvv est doit être une string de 3 chiffres"
                )
            with db.atomic():
                order = Order.get_by_id(id)
                if not order.email or not order.shipping_informations.first():
                    raise Exc.MissingFields(
                        422,
                        "order",
                        "Les informations du client sont nécessaire avant d'appliquer une carte de crédit",
                    )
                if order.paid:
                    raise ApiException("already-paid")(
                        422, "order", "La commande a déjà été payée."
                    )
                credit_card = json_payload["credit_card"]

                payment_payload = {
                    "credit_card": credit_card,
                    "amount_charged": order.shipping_price,
                }

                payment_response = http_post(
                    "" + THIRD_PARTY_PAYMENT_URL, dict=payment_payload
                )
                current_app.logger.debug(
                    f"Payment API response: {payment_response.status_code}"
                )

                payment_service_error = Exc.ThirdParty(
                    502,
                    "third_party",
                    "Le service de paiment tier ne fonctionne pas normalement. Paiement annulé.",
                )

                if not payment_response.ok:
                    try:
                        error_response = payment_response.json()
                        current_app.logger.debug(
                            f"Payment API response json: {payment_response.status_code}"
                        )
                        return error_response, payment_response.status_code
                    except JSONDecodeError:
                        if 400 <= payment_response.status_code < 500:
                            raise Exc.CardDeclined(
                                payment_response.status_code,
                                "credit_card",
                                "La carte de crédit a été déclinée",
                            )
                        else:
                            raise payment_service_error

                ok_response_schema = {
                    "credit_card": {
                        "name": str,
                        "first_digits": str,
                        "last_digits": str,
                        "expiration_year": int,
                        "expiration_month": int,
                    },
                    "transaction": {
                        "id": str,
                        "success": bool,
                        "amount_charged": float,
                    },
                }

                payment_json_response = payment_response.json()
                current_app.logger.debug(
                    f"Payment API response json: {payment_json_response}"
                )
                if not follows_schema(payment_json_response, ok_response_schema):
                    raise payment_service_error

                transaction = payment_json_response["transaction"]
                CreditCard.insert(
                    order=order,
                    cvv=credit_card["cvv"],
                    name=credit_card["name"],
                    number=credit_card["number"],
                    expiration_year=credit_card["expiration_year"],
                    expiration_month=credit_card["expiration_month"],
                ).on_conflict_replace().execute()

                Transaction.insert(
                    order=order,
                    id=transaction["id"],
                    success=transaction["success"],
                    amount_charged=transaction["amount_charged"],
                ).on_conflict_replace().execute()

                if transaction["amount_charged"] != order.shipping_price:
                    current_app.logger.warning(
                        f"Warning: The amount charged ({payment_json_response['amount_charged']}) does not match the order's shipping price ({order.shipping_price})"
                    )

                order.paid = payment_response.ok
                order.save()
            return get_order_by_id(order.id)
        else:
            raise ValidationError(
                "neither client information nor credit card information provided"
            )
    except DoesNotExist as err:
        current_app.logger.debug(f"{err!r}")
        return {}, 404  # HTTP_404 Not Found
    except ValidationError as err:
        current_app.logger.debug(f"{err!r}")
        raise Exc.MissingFields(
            422, "order", "Il manque un ou plusieurs champs qui sont obligatoires"
        )
    except ApiException as err:
        current_app.logger.debug(err)
        return err.error()
    except Exception as err:
        current_app.logger.debug(f"{err!r}")
        return {}, 500  # HTTP_500 Internal Server Error
