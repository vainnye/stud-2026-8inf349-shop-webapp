import json
import os
from pathlib import Path
from pickle import GLOBAL

import requests
from flask import Flask, redirect, send_from_directory, url_for

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
from shop_webapp.util import fetch_and_upsert_products, get_server_address

# PROJECT_FOLDER = Path(__file__).resolve().parent.parent.parent
PROJECT_FOLDER = Path.cwd().resolve()


app = Flask(
    __name__,
    static_folder=PROJECT_FOLDER / "static",
    instance_path=str(PROJECT_FOLDER / "instance"),
)
SERVER_ADDRESS = ""

with app.app_context():
    SERVER_ADDRESS = get_server_address()

# un dump de l'api du prof est dans "./res/data/products.json"
# cf. "Récupération des produits" dans le pdf
with app.app_context():
    fetch_and_upsert_products(
        local_file=os.environ.get("APP_PRODUCTS_FILE") or None
    )  # None si la variable est une string vide ou n'est pas set

if (os.environ.get("APP_USE_MOCKS") or "").upper() == "TRUE":
    from shop_webapp.mock import use_mocks

    with app.app_context():
        use_mocks()

app.logger.debug("initializing database")
db.connect()
db.create_tables(
    [Product, Order, OrderProduct, CreditCard, ShippingInformation, Transaction]
)
db.close()
app.logger.debug("database initialized")


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
app.logger.debug(f"api available at {SERVER_ADDRESS}/api/")
app.logger.debug(
    "all api endpoints available: "
    + "; ".join(
        [
            f"{r.rule!r} ({', '.join(r.methods or set())})"
            for r in app.url_map.iter_rules()
            if r.endpoint.startswith("api.")
        ]
    )
)


@app.get("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico")  # type: ignore


@app.get("/")
def hello_world():
    return """
    <div style="display: grid; place-items: center; height: 100vh;">
        <h1>Hello, World!</h1>
    </div>
    """
