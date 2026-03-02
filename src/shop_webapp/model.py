from peewee import (
    AutoField,
    BooleanField,
    CharField,
    CompositeKey,
    DecimalField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

"""
## Good practices

les noms des backrefs (dans ForeignKeyField) sont toujours au pluriel,
même si les contraintes de la BD ne permettent pas d'avoir plusieurs backrefs
Dans tous les cas ce sera une liste
"""

db = SqliteDatabase("database.db")


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
    price = DecimalField(decimal_places=2)

    def __str__(self):
        return f"Product(id={self.id!r}, name={self.name!r}, price={self.price!r})"


class Order(BaseModel):
    id = AutoField(primary_key=True)
    total_price = DecimalField(decimal_places=2, null=True)
    total_price_tax = DecimalField(decimal_places=2, null=True)
    email = CharField(null=True)

    def __str__(self):
        return f"Order(id={self.id!r}, email={self.email!r}, total_price={self.total_price!r})"


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="products")
    product = ForeignKeyField(Product, backref="orders")
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
    order = ForeignKeyField(Order, primary_key=True, backref="shipping_informations")
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
    success = BooleanField()
    amount_charged = DecimalField(decimal_places=2)

    def __str__(self):
        return f"Transaction(order_id={self.order.id!r}, id={self.id!r}, success={self.success!r}, amount_charged={self.amount_charged!r})"
