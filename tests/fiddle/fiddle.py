from shop_webapp.model import ShippingInformation

i = ShippingInformation.get_or_none(ShippingInformation.order == 2)

print(i)
