import click
from flask import current_app
from flask.cli import with_appcontext

from .db import database_proxy
from .models import get_all_models


def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_products_command)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create all database tables."""
    db = database_proxy.obj
    db.connect(reuse_if_open=True)
    db.create_tables(get_all_models(), safe=True)
    click.echo("Database initialized.")


@click.command("seed-products")
@with_appcontext
def seed_products_command():
    """Fetch remote products and persist them locally (idempotent)."""
    from .services.products import seed_products_if_empty

    db = database_proxy.obj
    db.connect(reuse_if_open=True)
    count = seed_products_if_empty(current_app.config["PRODUCTS_URL"])
    click.echo(f"Persisted {count} new products.")
