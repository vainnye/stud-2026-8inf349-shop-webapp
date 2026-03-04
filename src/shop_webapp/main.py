import os

from flask import Flask, send_from_directory

from shop_webapp.api import api
from shop_webapp.globals import (
    API_URL_PATH,
    INIT_PRODUCTS_LOCATION,
    INSTANCE_FOLDER,
    SERVER_ADDRESS,
    STATIC_FOLDER,
    USE_MOCKS,
    init_globals,
)
from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
    db,
)
from shop_webapp.util import fetch_and_upsert_products

app = Flask(
    __name__,
    static_folder=STATIC_FOLDER,
    instance_path=str(INSTANCE_FOLDER),
)

init_globals(app)

# c'est le dossier dans lequel va la BD
if not os.path.exists(INSTANCE_FOLDER):
    os.makedirs(INSTANCE_FOLDER)


with app.app_context():
    fetch_and_upsert_products(location=INIT_PRODUCTS_LOCATION)

if USE_MOCKS:
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


# -----------------
# adding endpoints
# -----------------

# adding the api endpoints
app.register_blueprint(api, url_prefix=API_URL_PATH.as_posix())
app.logger.debug(f"api available at {SERVER_ADDRESS}{API_URL_PATH.as_posix()}/")
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
