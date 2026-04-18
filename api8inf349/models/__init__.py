from peewee import Model

from ..db import database_proxy


class BaseModel(Model):
    class Meta:
        database = database_proxy


def get_all_models():
    """Return all concrete models used for table creation."""
    return []
