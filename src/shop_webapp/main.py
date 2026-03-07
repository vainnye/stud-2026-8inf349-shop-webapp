import os
import shutil

from flask import Flask, send_from_directory

from shop_webapp.api import api
from shop_webapp.globals import (
    API_URL_PATH,
    DATABASE_FILE,
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


@app.cli.command("init-db")
def init_db_command():
    """Initialise la base de données."""
    
    # réinitialiser la base de données
    try:
        os.remove(DATABASE_FILE)
    except FileNotFoundError:
        pass
    os.makedirs(INSTANCE_FOLDER, exist_ok=True)
    
    db.connect(reuse_if_open=True)

    db.create_tables([
        Product,
        Order,
        OrderProduct,
        ShippingInformation,
        CreditCard,
        Transaction,
    ])

    db.close()

    app.logger.debug("Database initialized.")


if not os.path.exists(DATABASE_FILE):
    app.logger.debug("Database file not found. please init the database using 'flask init-db'")

fetch_and_upsert_products(app, location=INIT_PRODUCTS_LOCATION)

if USE_MOCKS:
    from shop_webapp.mock import use_mocks

    use_mocks(app)


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
