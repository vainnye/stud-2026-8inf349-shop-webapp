import requests

from shop_webapp.model import Product

# retrieving products on startup
try:
    response = requests.get("http://dimensweb.uqac.ca/~jgnault/shops/products/")
    response.raise_for_status()
    json_response = response.json()
except requests.exceptions.RequestException as e:
    raise RuntimeError("failed to retrieve products on startup") from e
except ValueError as e:
    raise RuntimeError("failed to retrieve products on startup") from e

Product.insert_many(
    json_response["products"],
    fields=[
        Product.id,
        Product.name,
        Product.description,
        Product.image,
        Product.in_stock,
        Product.weight,
        Product.price,
    ],
).on_conflict_replace().execute()
