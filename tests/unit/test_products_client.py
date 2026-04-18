import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from inf349.clients.products import ProductsClientError, fetch_products


def _mock_context(body: str):
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    ctx = MagicMock()
    ctx.__enter__.return_value = resp
    ctx.__exit__.return_value = False
    return ctx


def test_fetch_products_returns_list():
    payload = json.dumps({"products": [{"id": 1, "name": "A", "price": 1.0}]})
    with patch(
        "inf349.clients.products.urlopen",
        return_value=_mock_context(payload),
    ):
        products = fetch_products("http://fake/")
    assert products == [{"id": 1, "name": "A", "price": 1.0}]


def test_fetch_products_raises_on_invalid_json():
    with patch(
        "inf349.clients.products.urlopen",
        return_value=_mock_context("not json"),
    ):
        with pytest.raises(ProductsClientError):
            fetch_products("http://fake/")


def test_fetch_products_raises_on_missing_products_key():
    payload = json.dumps({"items": []})
    with patch(
        "inf349.clients.products.urlopen",
        return_value=_mock_context(payload),
    ):
        with pytest.raises(ProductsClientError):
            fetch_products("http://fake/")


def test_fetch_products_raises_on_network_error():
    with patch(
        "inf349.clients.products.urlopen",
        side_effect=URLError("boom"),
    ):
        with pytest.raises(ProductsClientError):
            fetch_products("http://fake/")
