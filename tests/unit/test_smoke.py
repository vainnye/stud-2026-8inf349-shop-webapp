from inf349 import create_app
from inf349.config import TestConfig
from inf349.db import database_proxy


def test_app_factory_builds_app():
    app = create_app(TestConfig)
    assert app is not None
    assert app.config["TESTING"] is True


def test_database_proxy_is_initialized(app):
    assert database_proxy.obj is not None


def test_init_db_command_runs(runner):
    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    assert "Database initialized" in result.output
