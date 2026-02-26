from peewee import (
    BooleanField,
    CharField,
    DecimalField,
    IntegerField,
    Model,
    TextField,
)

from model.db import db

"""
NOTA:
pour `price` je me fie aux exemples de l'énoncé : `29.45`, `28.1` même s'il y a écrit "en cents" dans les consignes
tant qu'on a les centimes ça devrait être bon I guess


"""


class Product(Model):
    name = CharField()
    description = TextField()
    image = CharField()
    in_stock = BooleanField()
    weight = IntegerField()
    price = DecimalField(decimal_places=2)

    class Meta:
        database = db
