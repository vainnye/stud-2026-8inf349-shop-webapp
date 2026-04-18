from flask import Flask

from .config import get_config
from .db import database_proxy, init_database
from .cli import register_cli
from .routes import register_blueprints


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_object(config or get_config())

    db = init_database(app.config["DATABASE_URL"])

    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()

    register_blueprints(app)
    register_cli(app)

    return app
