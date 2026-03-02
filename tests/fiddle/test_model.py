from shop_webapp.model import Product

un_produit = Product(
    name="xxx", description="zz", image="ee", in_stock=True, weight=111, price=123
)
un_produit.save()


select = Product.select().dicts()
print(f"there are {select.count()} products:")
if select.count() > 0:
    for un_produit in select:
        un_produit: Product
        print(un_produit)
