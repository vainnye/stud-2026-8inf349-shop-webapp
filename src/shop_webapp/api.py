"""
Api endpoints
"""

from logging import getLogger

from flask import Blueprint, current_app

from shop_webapp.model import Product

log = getLogger(__name__)

api = Blueprint("api", __name__)


@api.get("/products/")
def get_products():
    """Get a list of all products."""
    # selecting only the fields required by the api specs
    products = Product.select(
        Product.name,
        Product.id,
        Product.in_stock,
        Product.description,
        Product.price,
        Product.weight,
        Product.image,
    )
    current_app.logger.debug(f"listed {products.count()} products")
    return {"products": list(products.dicts())}
