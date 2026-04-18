import click
from flask.cli import with_appcontext

from .db import database_proxy
from .models import get_all_models


def register_cli(app):
    app.cli.add_command(init_db_command)


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create all database tables."""
    db = database_proxy.obj
    db.connect(reuse_if_open=True)
    db.create_tables(get_all_models(), safe=True)
    click.echo("Database initialized.")
