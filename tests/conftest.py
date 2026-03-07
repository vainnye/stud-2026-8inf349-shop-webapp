import os
import pytest

@pytest.fixture(scope="session", autouse=True)
def _set_test_env():
    """
    Force the app to run fully local for tests:
    - products from local file
    - payment via mocks
    """
    os.environ["API_PRODUCTS_LOCATION"] = "./res/data/products.json"
    os.environ["API_USE_MOCKS"] = "True"
    # If your app uses another env var for DB path, add it here later.


@pytest.fixture()
def app():
    """
    pytest-flask expects a fixture named `app` returning a Flask instance.
    We try common import patterns, adjust if needed.
    """
    # Pattern 1: module exposes `app`
    try:
        from shop_webapp import app as flask_app
    except Exception:
        # Pattern 2: app defined in another file (adjust if your repo differs)
        from shop_webapp.main import app as flask_app  # noqa: F401

    flask_app.config.update(
        TESTING=True,
    )
    return flask_app


@pytest.fixture()
def client(app):
    return app.test_client()