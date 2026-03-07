from __future__ import annotations

from peewee import (
    AutoField,
    BooleanField,
    CharField,
    CompositeKey,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from shop_webapp.globals import DATABASE_FILE

"""
## Good practices

les noms des backrefs (dans ForeignKeyField) sont toujours au pluriel,
même si les contraintes de la BD ne permettent pas d'avoir plusieurs backrefs
Dans tous les cas ce sera une liste
"""

db = SqliteDatabase(str(DATABASE_FILE))


class BaseModel(Model):
    class Meta:
        database = db


class Product(BaseModel):
    id = AutoField(primary_key=True)
    name = CharField()
    description = TextField()
    image = CharField()
    in_stock = BooleanField()
    weight = IntegerField()
    price = FloatField()

    def __str__(self):
        return f"Product(id={self.id!r}, name={self.name!r}, price={self.price!r})"


class Order(BaseModel):
    id = AutoField(primary_key=True)
    email = CharField(null=True)
    total_price = FloatField(null=True)
    total_price_tax = FloatField(null=True)
    shipping_price = FloatField(null=True)
    paid = BooleanField()

    def __str__(self):
        return f"Order(id={self.id!r}, email={self.email!r}, total_price={self.total_price!r})"

    def calc_total_price(self, price, quantity):
        self.total_price = price * quantity

    def calc_total_price_tax(self, total_price, province):
        match province:
            case "QC":
                coef = 1.15
            case "ON":
                coef = 1.13
            case "AB":
                coef = 1.05
            case "BC":
                coef = 1.12
            case "NS":
                coef = 1.14
            case _:
                coef = 1.10  # taxe par défaut
                # TODO: faire des recherches sur les taxes

        self.total_price_tax = total_price * coef

    def calc_shipping_price(self, total_price_tax, weight, quantity):
        total_weight = weight * quantity
        if total_weight < 500:
            shipping_fee = 5
        elif 500 <= total_weight < 2000:
            shipping_fee = 10
        else:
            shipping_fee = 25

        self.shipping_price = total_price_tax + shipping_fee


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="order_products")
    product = ForeignKeyField(Product, backref="order_products")
    quantity = IntegerField()

    class Meta:  # type: ignore
        primary_key = CompositeKey("order", "product")

    def __str__(self):
        return f"OrderProduct(order_id={self.order.id!r}, product_id={self.product.id!r}, quantity={self.quantity!r})"


class CreditCard(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="credit_cards")
    name = CharField()
    number = CharField()
    expiration_year = IntegerField()
    cvv = CharField()
    expiration_month = IntegerField()

    def __str__(self):
        return f"CreditCard(order_id={self.order.id!r}, name={self.name!r}, number={self.number!r})"


class ShippingInformation(BaseModel):
    order = ForeignKeyField(
        Order, primary_key=True, backref="shipping_informations"
    )  # puting an s at the end for uniformity even though not grammaticaly correct
    country = CharField()
    address = CharField()
    postal_code = CharField()
    city = CharField()
    province = CharField()

    def __str__(self):
        return f"ShippingInformation(order_id={self.order.id!r}, address={self.address!r}, city={self.city!r}, country={self.country!r})"


class Transaction(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="transactions")
    id = CharField(unique=True)
    success = CharField()  # c'était bool dans le pdf mais la vraie API renvoie un str
    amount_charged = FloatField()

    def __str__(self):
        return f"Transaction(order_id={self.order.id!r}, id={self.id!r}, success={self.success!r}, amount_charged={self.amount_charged!r})"
