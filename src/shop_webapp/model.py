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


class Order(BaseModel):
    id = AutoField(primary_key=True)
    total_price = DecimalField(decimal_places=2)
    total_price_tax = DecimalField(decimal_places=2)
    email = CharField()


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="products")
    product = ForeignKeyField(Product, backref="orders")
    quantity = IntegerField()

    class Meta:
        primary_key = CompositeKey("order", "product")


class CreditCard(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="credit_card")
    name = CharField()
    number = CharField()
    expiration_year = IntegerField()
    cvv = CharField()
    expiration_month = IntegerField()


class ShippingInformation(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="shipping_information")
    country = CharField()
    address = CharField()
    postal_code = CharField()
    city = CharField()
    province = CharField()


class Transaction(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="transaction")
    amount = DecimalField(decimal_places=2)
    credit_card = ForeignKeyField(CreditCard)
    shipping_information = ForeignKeyField(ShippingInformation)
