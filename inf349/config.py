import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///shop.db")

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
