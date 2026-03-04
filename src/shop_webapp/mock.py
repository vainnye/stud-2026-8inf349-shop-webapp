import os
import random
import string

from flask import current_app, request

import shop_webapp.api as api_module
from shop_webapp.api import API_URL_PREFIX, api
from shop_webapp.util import ValidationError, get_server_address, validate_schema


def use_mocks():
    SERVER_ADDRESS = get_server_address()

    THIRD_PARTY_PAYMENT_URL = "/mocks/shops/pay/"
    api_module.THIRD_PARTY_PAYMENT_COMPLETE_URL = (
        SERVER_ADDRESS + API_URL_PREFIX.removesuffix("/") + THIRD_PARTY_PAYMENT_URL
    )

    current_app.logger.warning("Using mocks")

    current_app.logger.warning(
        f"Using mock payment API: {api_module.THIRD_PARTY_PAYMENT_COMPLETE_URL}"
    )

    @api.post(THIRD_PARTY_PAYMENT_URL)
    def third_party_api():
        current_app.logger.warning("Using mock payment API")
        try:
            json_payload = request.get_json()
            schema = {
                "credit_card": {
                    "name": str,
                    "number": str,
                    "expiration_month": int,
                    "expiration_year": int,
                    "cvv": str,
                },
                "amount_charged": float,
            }
            validate_schema(json_payload, schema)
            credit_card = json_payload["credit_card"]
            amount_charged = json_payload["amount_charged"]

            is_declined = random.random() > 0.5

            if not is_declined:
                number = credit_card["number"].replace("-", "").replace(" ", "")

                if not number.isnumeric() or not len(number) == 16:
                    raise ValueError(
                        "Le numéro de carte de crédit doit être un nombre à 16 chiffres"
                    )

                return {
                    "credit_card": {
                        "name": credit_card["name"],
                        "first_digits": number[:4],
                        "last_digits": number[-4:],
                        "expiration_year": 2024,
                        "expiration_month": 9,
                    },
                    "transaction": {
                        "id": "".join(
                            random.choice(string.ascii_letters + string.digits)
                            for _ in range(32)
                        ),
                        "success": True,
                        "amount_charged": amount_charged,
                    },
                }, 200
            else:
                error_msg = "La carte de crédit a été déclinée. (c'est un mock testing randomisé)"
            return {
                "errors": {
                    "credit_card": {
                        "code": "card-declined",
                        "name": error_msg,
                    }
                }
            }, 422  # HTTP_422 Unprocessable Entity
        except ValueError as err:
            current_app.logger.exception(f"Error in third_party_api {err!r}")
            return {"error": {"code": "invalid-card-number", "message": str(err)}}, 422
        except ValidationError as err:
            current_app.logger.exception(f"Error in third_party_api {err!r}")
            return {"error": {"code": "missing-fields", "message": repr(err)}}, 422
        except Exception as err:
            current_app.logger.exception(f"Error in third_party_api {err!r}")
            return {"error": {"code": "server-error", "message": repr(err)}}, 500
