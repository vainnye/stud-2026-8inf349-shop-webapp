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

    def __str__(self):
        return f"Product(id={self.id}, name='{self.name}', price={self.price})"


class Order(BaseModel):
    id = AutoField(primary_key=True)
    total_price = DecimalField(decimal_places=2)
    total_price_tax = DecimalField(decimal_places=2)
    email = CharField()

    def __str__(self):
        return (
            f"Order(id={self.id}, email='{self.email}', total_price={self.total_price})"
        )


class OrderProduct(BaseModel):
    order = ForeignKeyField(Order, backref="products")
    product = ForeignKeyField(Product, backref="orders")
    quantity = IntegerField()

    class Meta:
        primary_key = CompositeKey("order", "product")

    def __str__(self):
        return f"OrderProduct(order_id={self.order.id}, product_id={self.product.id}, quantity={self.quantity})"


class CreditCard(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="credit_card")
    name = CharField()
    number = CharField()
    expiration_year = IntegerField()
    cvv = CharField()
    expiration_month = IntegerField()

    def __str__(self):
        return f"CreditCard(order_id={self.order.id}, name='{self.name}', number='****{self.number[-4:]}')"


class ShippingInformation(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="shipping_information")
    country = CharField()
    address = CharField()
    postal_code = CharField()
    city = CharField()
    province = CharField()

    def __str__(self):
        return f"ShippingInformation(order_id={self.order.id}, address='{self.address}', city='{self.city}', country='{self.country}')"


class Transaction(BaseModel):
    order = ForeignKeyField(Order, primary_key=True, backref="transaction")
    amount = DecimalField(decimal_places=2)
    credit_card = ForeignKeyField(CreditCard)
    shipping_information = ForeignKeyField(ShippingInformation)

    def __str__(self):
        return f"Transaction(order_id={self.order.id}, amount={self.amount})"
