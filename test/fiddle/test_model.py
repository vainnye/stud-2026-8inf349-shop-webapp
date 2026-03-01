from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
    db,
)

db.connect()
db.create_tables(
    [Product, Order, OrderProduct, CreditCard, ShippingInformation, Transaction]
)


p = Product(
    name="xxx", description="zz", image="ee", in_stock=True, weight=111, price=123
)
p.save()
