import random
import string

from flask import Flask, current_app, request

import shop_webapp.globals as _globals
from shop_webapp.api import api
from shop_webapp.globals import (
    API_URL_PATH,
    MOCK_API_PAYMENT_PATH,
    SERVER_ADDRESS,
    THIRD_PARTY_PAYMENT_URL,
)
from shop_webapp.util import ValidationError, validate_schema


def use_mocks(app: Flask):
    with app.app_context():
        _use_mocks()


def _use_mocks():
    _globals.THIRD_PARTY_PAYMENT_URL = (
        SERVER_ADDRESS + (API_URL_PATH / MOCK_API_PAYMENT_PATH).as_posix()
    )

    current_app.logger.warning("Using mocks")

    current_app.logger.warning(f"Using mock payment API: {THIRD_PARTY_PAYMENT_URL}")

    @api.post(MOCK_API_PAYMENT_PATH.as_posix() + "/")
    def third_party_api():
        """
        Mock endpoint for third-party payment API.

        This endpoint simulates a payment gateway for testing purposes.
        It randomly approves or declines credit card transactions.

        example request body:
        {
            "credit_card": {
                "name": "John Doe",
                "number": "4242 4242 4242 4242",
                "expiration_year": 2029,
                "cvv": "123",
                "expiration_month" : 9
            }
        }

        example response body on succes (HTTP 200):
        {
            "credit_card": {
                "name": "John Doe",
                "first_digits": "4242",
                "last_digits": "4242",
                "expiration_year": 2024,
                "expiration_month": 9,
            },
            "transaction": {
                "id": "wgEQ4zAUdYqpr21rt8A10dDrKbfcLmqi",
                "success": "true",
                "amount_charged": 10148,
            },
        }

        example response body on error (HTTP 422 for this example):
        {
            "errors": {
                "credit_card": {
                    "code": "card-declined",
                    "name": "La carte de crédit a été déclinée",
                }
            }
        }
        """
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
                        # success était bool dans le pdf mais la vraie API renvoie un str
                        "success": "true",
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
