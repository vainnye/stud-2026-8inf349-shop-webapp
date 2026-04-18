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
        raise NotImplementedError(
            "PostgreSQL support is reserved for partie 2."
        )

    raise ValueError(f"Unsupported database scheme: {scheme!r}")


def init_database(url: str):
    db = _build_database(url)
    database_proxy.initialize(db)
    return db
