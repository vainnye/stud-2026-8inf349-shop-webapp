import logging
from typing import Callable, Dict, Iterable, List, Optional

from ..clients.products import ProductsClientError, fetch_products
from ..models import Product

log = logging.getLogger(__name__)


_PRODUCT_FIELDS = {
    "name",
    "description",
    "image",
    "weight",
    "price",
    "in_stock",
}


def _sanitize(raw: Dict) -> Dict:
    return {k: raw[k] for k in _PRODUCT_FIELDS if k in raw}


def save_products(raw_products: Iterable[Dict]) -> int:
    """Persist products locally. Idempotent: existing ids are left untouched.

    Returns the number of new rows created.
    """
    count = 0
    for raw in raw_products:
        if not isinstance(raw, dict):
            continue
        pid = raw.get("id")
        if pid is None or raw.get("name") is None or raw.get("price") is None:
            continue
        _, created = Product.get_or_create(id=pid, defaults=_sanitize(raw))
        if created:
            count += 1
    return count


def seed_products_if_empty(
    url: str,
    fetcher: Optional[Callable[[str], List[Dict]]] = None,
) -> int:
    """Fetch and persist products only when the local table is empty.

    Remote errors are logged and swallowed so app startup is not blocked.
    """
    if Product.select().exists():
        return 0

    fetcher = fetcher or fetch_products
    try:
        raw_products = fetcher(url)
    except ProductsClientError as exc:
        log.warning("Products bootstrap: remote fetch failed: %s", exc)
        return 0

    return save_products(raw_products)


def bootstrap_products(url: str) -> int:
    """Entry point called once at application startup.

    No-op when the product table does not exist yet (e.g. before init-db).
    """
    if not Product.table_exists():
        log.info("Products bootstrap skipped: product table does not exist.")
        return 0
    return seed_products_if_empty(url)


def product_to_dict(product: Product) -> Dict:
    """Serialize a Product instance to the JSON shape required by the spec."""
    return {
        "name": product.name,
        "id": product.id,
        "in_stock": product.in_stock,
        "description": product.description,
        "price": product.price,
        "weight": product.weight,
        "image": product.image,
    }


def list_products() -> List[Dict]:
    """Return every product from the local database, ordered by id."""
    return [product_to_dict(p) for p in Product.select().order_by(Product.id)]
