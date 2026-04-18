import json
from typing import Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 10


class ProductsClientError(Exception):
    """Raised when the remote products service cannot be reached or parsed."""


def fetch_products(url: str, timeout: float = DEFAULT_TIMEOUT) -> List[Dict]:
    """Fetch the remote products catalog.

    Returns the raw products list from the remote API.
    Raises ProductsClientError on network, HTTP or payload errors.
    """
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except (URLError, OSError) as exc:
        raise ProductsClientError(f"HTTP error: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProductsClientError(f"Invalid JSON: {exc}") from exc

    products = payload.get("products")
    if not isinstance(products, list):
        raise ProductsClientError("Missing or invalid 'products' in payload")
    return products
