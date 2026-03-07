from inf349.model import Order, OrderProduct, Product, Transaction

o = (
    Order.insert(id=1, total_price=123, total_price_tax=1234, email="azbc")
    .on_conflict_replace()
    .execute()
)
o = Order.get_by_id(1)
print(o)

p = Product.get_by_id(1)
print(p)

OrderProduct.insert(product=p, order=o, quantity=2).on_conflict_replace().execute()
op = OrderProduct.get()
print(op)

Transaction.insert(
    order=o, id="abc", amount_charged=123, success=True
).on_conflict_replace().execute()
t = Transaction.get_by_id(o)
print(t)

print(list(o.order_products))
print(list(o.transactions))
