import json

import requests
from flask import Flask

from shop_webapp.api import API_URL_PREFIX, api
from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
    db,
)

app = Flask(__name__)


def fetch_and_upsert_products(load_from_local_file=True):
    """
    Fetches product data from a remote API and upserts it into the local Product table.

    cf. "Récupération des produits" dans le pdf
    """
    if not load_from_local_file:
        try:
            response = requests.get("http://dimensweb.uqac.ca/~jgnault/shops/products/")
            response.raise_for_status()
            json_response = response.json()
        except requests.exceptions.RequestException as e:
            msg = "failed to retrieve products on startup"
            app.logger.debug(msg)
            raise RuntimeError(msg) from e
        except ValueError as e:
            msg = "failed to retrieve products on startup"
            app.logger.debug(msg)
            raise RuntimeError(msg) from e
        app.logger.debug("products fetched on startup")
    else:
        app.logger.debug("products loaded from local file")
        with open("./res/data/products.json") as f:
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
    app.logger.debug("database product list is up to date")


app.logger.debug("initializing database")
db.connect()
db.create_tables(
    [Product, Order, OrderProduct, CreditCard, ShippingInformation, Transaction]
)
db.close()
app.logger.debug("database initialized")

# fetch_and_upsert_products(load_from_local_file=True)  # development only
fetch_and_upsert_products()
# cf. "Récupération des produits" dans le pdf


@app.before_request
def before_request():
    db.connect()


@app.after_request
def after_request(response):
    db.close()
    return response


# -----------------
# adding endpoints
# -----------------

# adding the api endpoints
app.register_blueprint(api, url_prefix=API_URL_PREFIX)
app.logger.debug("api available at http://127.0.0.1:5000/api/")
app.logger.debug(
    f"all api available resources: {[r.rule for r in app.url_map.iter_rules() if r.endpoint.startswith('api.')]}"
)


@app.get("/")
def hello_world():
    return """
    <div style="display: grid; place-items: center; height: 100vh;">
        <h1>Hello, World!</h1>
    </div>
    """
