from urllib.parse import urlparse

from peewee import DatabaseProxy, SqliteDatabase

database_proxy = DatabaseProxy()


def _build_database(url: str):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme in ("sqlite", ""):
        path = parsed.path.lstrip("/")
        if not path or path == ":memory:":
            return SqliteDatabase(":memory:")
        return SqliteDatabase(path)

    if scheme in ("postgres", "postgresql"):
        from peewee import PostgresqlDatabase
        # urlparse gives path as "/dbname" — strip the leading slash.
        db_name = parsed.path.lstrip("/")
        return PostgresqlDatabase(
            db_name,
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
        )

    raise ValueError(f"Unsupported database scheme: {scheme!r}")


def init_database(url: str):
    db = _build_database(url)
    database_proxy.initialize(db)
    return db
