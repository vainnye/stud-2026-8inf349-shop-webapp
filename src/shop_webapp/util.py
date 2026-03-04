import json as _json
import urllib.error
import urllib.request
from email.message import Message

from flask import Flask
from flask.globals import current_app

from shop_webapp.model import Product

# ---------------------------------------------
#    minimal api data validation helpers
# ---------------------------------------------


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


# ---------------------------------------
#       Product list initialization
# ---------------------------------------


def fetch_and_upsert_products(app: Flask, location: str):
    """
    Fetches product data from a remote API and upserts it into the local Product table.

    cf. "Récupération des produits" dans le pdf
    """
    with app.app_context():
        _fetch_and_upsert_products(location)


def _fetch_and_upsert_products(location: str):
    """
    Fetches product data from a remote API and upserts it into the local Product table.

    cf. "Récupération des produits" dans le pdf
    """
    if location.startswith("https://") or location.startswith("http://"):
        current_app.logger.debug(f"Fetching products from remote API: {location}")
        try:
            response = http_get(location)
            response.raise_for_status()
            json_response = response.json()
        except (_json.JSONDecodeError, HTTPError) as e:
            msg = "failed to retrieve products on startup"
            current_app.logger.debug(msg)
            raise RuntimeError(msg) from e
        current_app.logger.debug("products fetched on startup")
    else:
        current_app.logger.debug(f"Loading products from local file: {location}")
        with open(location) as f:
            json_response = _json.load(f)
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
            current_app.logger.debug("database product list is up to date")


# ----------------------------------------------------
#           requests library minimum replacement
# ----------------------------------------------------

HTTPError = urllib.error.HTTPError


class _HttpResponse:
    def __init__(self, status_code: int, content: bytes, headers: Message) -> None:
        self.status_code = status_code
        self.ok = not (400 <= self.status_code < 600)  # as in the requests library
        self.content = content
        self.headers = headers

    @property
    def text(self):
        return self.content.decode("utf-8")

    def json(self):
        """raises JSONDecodeError if couldn't decode json"""
        return _json.loads(self.text)

    def raise_for_status(self):
        """raises HTTPError if status code indicates an error"""
        if not self.ok:
            raise urllib.error.HTTPError(
                url="", code=self.status_code, msg=self.text, hdrs=self.headers, fp=None
            )

    def __str__(self):
        # Limit the displayed text to the first 100 characters for brevity
        limited_text = self.text
        if len(limited_text) > 42:
            limited_text = limited_text[:42] + "..."
        return f"<_HttpResponse status_code={self.status_code} text={limited_text!r}>"


def _http_request(method: str, url: str, json: dict | None = None):
    req = urllib.request.Request(url=url, method=method)

    if json is not None:
        req.data = bytes(_json.dumps(json), encoding="utf-8")
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
            status_code = resp.status
            headers = resp.headers
    except urllib.error.HTTPError as e:
        status_code = e.code
        content = e.read()
        headers = e.headers

    return _HttpResponse(status_code, content, headers)


def http_post(url: str, json: dict):
    return _http_request("POST", url, json)


def http_get(url: str):
    return _http_request("GET", url)


str(
    http_post(
        "http://dimensweb.uqac.ca/~jgnault/shops/pay/",
        {
            "credit_card": {
                "name": "John Doe",
                "number": "4242 4242 4242 4242",
                "expiration_year": 2029,
                "cvv": "123",
                "expiration_month": 9,
            }
        },
    )
)
