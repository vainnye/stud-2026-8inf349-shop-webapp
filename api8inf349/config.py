import os


def _build_database_url() -> str:
    """Build a database URL from environment variables.

    Priority:
    1. Individual DB_* vars (partie 2 / production) → postgresql://
    2. DATABASE_URL env var (legacy / CI override)
    3. SQLite fallback (local dev without any env vars set)
    """
    host = os.environ.get("DB_HOST")
    if host:
        user = os.environ.get("DB_USER", "")
        password = os.environ.get("DB_PASSWORD", "")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "api8inf349")
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return os.environ.get("DATABASE_URL", "sqlite:///shop.db")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATABASE_URL = _build_database_url()

    PRODUCTS_URL = os.environ.get(
        "PRODUCTS_URL",
        "https://dimensweb.uqac.ca/~jgnault/shops/products/",
    )
    PAYMENT_URL = os.environ.get(
        "PAYMENT_URL",
        "https://dimensweb.uqac.ca/~jgnault/shops/pay/",
    )

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    TESTING = False
    DEBUG = False


class DevConfig(Config):
    DEBUG = True


class TestConfig(Config):
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"


_CONFIGS = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": Config,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return _CONFIGS.get(env, DevConfig)
