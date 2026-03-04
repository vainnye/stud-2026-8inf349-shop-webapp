import json

import requests
from flask.globals import current_app

from shop_webapp.model import Product, db


def validate_schema(data, schema):
    """
    Validates a data dict against a schema dict of types.
    Raises TypeError if types don't match.
    Raises KeyError if a required field is missing.
    """
    if not isinstance(data, dict):
        raise ValidationIncorrectValue(f"Expected dict, got {type(data).__name__}")

    for key, expected_type in schema.items():
        # 1. Check if the key exists
        if key not in data:
            raise ValidationMissingField(f"Missing required field: '{key}'")

        value = data[key]

        # 2. If the schema specifies a nested dict, recurse
        if isinstance(expected_type, dict):
            validate_schema(value, expected_type)

        # 3. Otherwise, check the type directly
        elif not isinstance(value, expected_type):
            raise ValidationIncorrectValue(
                f"Field '{key}' expected {expected_type.__name__}, "
                f"got {type(value).__name__} (value: {value})"
            )

    return True


def follows_schema(data, schema):
    try:
        validate_schema(data, schema)
        return True
    except ValidationError:
        return False


class ValidationError(Exception):
    """Custom exception for schema validation errors."""


class ValidationMissingField(Exception):
    """Custom exception for schema validation errors."""


class ValidationIncorrectValue(Exception):
    """Custom exception for schema validation errors."""


def fetch_and_upsert_products(location: str):
    """
    Fetches product data from a remote API and upserts it into the local Product table.

    cf. "Récupération des produits" dans le pdf
    """
    if location.startswith("https://") or location.startswith("http://"):
        try:
            response = requests.get(location)
            response.raise_for_status()
            json_response = response.json()
        except requests.exceptions.RequestException as e:
            msg = "failed to retrieve products on startup"
            current_app.logger.debug(msg)
            raise RuntimeError(msg) from e
        except ValueError as e:
            msg = "failed to retrieve products on startup"
            current_app.logger.debug(msg)
            raise RuntimeError(msg) from e
        current_app.logger.debug("products fetched on startup")
    else:
        current_app.logger.debug("products loaded from local file")
        with open(location) as f:
            json_response = json.load(f)
            db.connect()
            # upserting products
            Product.insert_many(
                json_response["products"],
                # on filtre les fields au cas-où l'api du prof en a en trop
                fields=[
                    Product.id,
                    Product.name,
                    Product.description,
                    Product.image,
                    Product.in_stock,
                    Product.weight,
                    Product.price,
                ],
            ).on_conflict_replace().execute()
            db.close()
            current_app.logger.debug("database product list is up to date")
