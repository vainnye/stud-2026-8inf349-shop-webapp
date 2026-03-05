import json

from playhouse.shortcuts import model_to_dict

from shop_webapp.api import place_order_for_product
from shop_webapp.model import (
    CreditCard,
    Order,
    OrderProduct,
    Product,
    ShippingInformation,
    Transaction,
)

# place_order_for_product(Product.get_by_id(1), 10)

order = Order.select().where(Order.id == 1).first()

response = model_to_dict(order)
response["transaction"] = order.transactions.dicts().first() or {}
response["credit_card"] = order.credit_cards.dicts().first() or {}
response["shipping_information"] = order.shipping_informations.dicts().first() or {}
order_product = order.order_products.first()
response["product"] = {
    "id": order_product.product.id,
    "quantity": order_product.quantity,
}

print(json.dumps(response))


# order_product = (
#     OrderProduct.select(OrderProduct, Product, Order)
#     .join(Order, on=(Order.id == OrderProduct.product))
#     .join(Product, on=(OrderProduct.product == Product.id))
#     .where(Order.id == 1)
#     .get()
# )

# print(order_product.product.price)
# print(order_product.product.weight)
# print(order_product.quantity)
# print()
# print(order_product.order.transactions)
# print(order_product.order.transactions.first())

# result = (
#     Order.select(Product.weight, Product.price, OrderProduct.quantity)
#     .join(OrderProduct, on=(Order.id == OrderProduct.product))
#     .join(Product, on=(OrderProduct.product == Product.id))
#     .where(Order.id == 1)
#     .limit(1)
#     .dicts()
#     .execute()
# )

# print(result[0])
