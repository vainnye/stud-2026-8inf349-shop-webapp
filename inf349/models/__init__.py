import json

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

from ..db import database_proxy


class JSONField(TextField):
    """Portable JSON field stored as TEXT.

    Compatible with SQLite (partie 1) and PostgreSQL (partie 2) without
    depending on playhouse dialect-specific fields.
    """

    def db_value(self, value):
        if value is None:
            return None
        return json.dumps(value)

    def python_value(self, value):
        if value is None:
            return None
        return json.loads(value)


class BaseModel(Model):
    class Meta:
        database = database_proxy


class Product(BaseModel):
    id = IntegerField(primary_key=True)
    name = CharField()
    description = TextField(null=True)
    image = CharField(null=True)
    weight = IntegerField(null=True)
    price = FloatField()
    in_stock = BooleanField(default=True)


class Order(BaseModel):
    id = AutoField()
    email = CharField(null=True)
    paid = BooleanField(default=False)
    shipping_information = JSONField(null=True)
    credit_card = JSONField(null=True)
    transaction = JSONField(null=True)


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="items", on_delete="CASCADE")
    product = ForeignKeyField(Product, backref="+")
    quantity = IntegerField(default=1)


def get_all_models():
    return [Product, Order, OrderProduct]
