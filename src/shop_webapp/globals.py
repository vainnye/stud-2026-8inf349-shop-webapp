# PROJECT_FOLDER = Path(__file__).resolve().parent.parent.parent
import os
from pathlib import Path

from flask import Flask


# Get the host and port using the same logic as Flask's run command
def get_server_address(app: Flask):
    """get server address as f'http://{host}:{port}'"""
    # Check SERVER_NAME config first
    server_name = app.config.get("SERVER_NAME")
    if server_name:
        host, _, port = server_name.partition(":")
        host = host or "127.0.0.1"
        port = int(port) if port else 5000
    else:
        host = "127.0.0.1"
        port = 5000

    return f"http://{host}:{port}"


USE_MOCKS = (os.environ.get("API_USE_MOCKS") or "").upper() == "TRUE"
INIT_PRODUCTS_LOCATION = (
    os.environ.get("API_PRODUCTS_LOCATION")
    or "http://dimensweb.uqac.ca/~jgnault/shops/products/"
)
# un dump de l'api du prof est dans "./res/data/products.json"
# cf. "Récupération des produits" dans le pdf

PROJECT_FOLDER = Path.cwd().resolve()
API_URL_PATH = Path("/api/")
INSTANCE_FOLDER = PROJECT_FOLDER / "instance"
STATIC_FOLDER = PROJECT_FOLDER / "static"
DATABASE_FILE = INSTANCE_FOLDER / "database.db"

MOCK_API_PAYMENT_PATH = Path("/mocks") / "shops" / "pay"

THIRD_PARTY_PAYMENT_URL = "http://dimensweb.uqac.ca/~jgnault/shops/pay/"
SERVER_ADDRESS = "http://127.0.0.1:5000"


def init_globals(app: Flask):
    global SERVER_ADDRESS
    SERVER_ADDRESS = get_server_address(app)
    if USE_MOCKS:
        global THIRD_PARTY_PAYMENT_URL
        THIRD_PARTY_PAYMENT_URL = (
            SERVER_ADDRESS + MOCK_API_PAYMENT_PATH.as_posix() + "/"
        )
