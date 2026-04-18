import pytest

from inf349 import create_app
from inf349.config import TestConfig
from inf349.db import database_proxy
from inf349.models import get_all_models


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def db(app):
    db = database_proxy.obj
    if db.is_closed():
        db.connect(reuse_if_open=True)
    db.create_tables(get_all_models(), safe=True)
    yield db
