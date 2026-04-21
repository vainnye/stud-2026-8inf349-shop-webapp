import click
from flask import current_app
from flask.cli import with_appcontext

from .db import database_proxy
from .models import get_all_models


def register_cli(app):
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_products_command)
    app.cli.add_command(worker_command)


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


@click.command("worker")
@with_appcontext
def worker_command():
    """Start an RQ worker that processes background payment tasks."""
    redis_url = current_app.config.get("REDIS_URL")
    if not redis_url:
        click.echo("REDIS_URL is not configured — worker cannot start.", err=True)
        return

    try:
        import redis as _redis
        from rq import Queue, Worker
    except ImportError:
        click.echo("rq / redis packages are not installed.", err=True)
        return

    conn = _redis.from_url(redis_url)
    q = Queue(connection=conn)
    worker = Worker([q], connection=conn)
    click.echo("RQ worker started. Waiting for payment jobs…")
    worker.work()
