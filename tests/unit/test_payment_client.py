import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from inf349.clients.payment import PaymentClientError, charge


def _mock_context(body: str):
    resp = MagicMock()
    resp.read.return_value = body.encode("utf-8")
    ctx = MagicMock()
    ctx.__enter__.return_value = resp
    ctx.__exit__.return_value = False
    return ctx


VALID_CARD = {
    "name": "John Doe",
    "number": "4242424242424242",
    "expiration_year": 2024,
    "cvv": "123",
    "expiration_month": 9,
}


def test_charge_returns_parsed_body_on_success():
    body = json.dumps({
        "credit_card": {"name": "John Doe", "first_digits": "4242"},
        "transaction": {"id": "tx_1", "success": True, "amount_charged": 33.0},
    })
    with patch(
        "inf349.clients.payment.urlopen",
        return_value=_mock_context(body),
    ):
        result = charge(33.0, VALID_CARD, url="http://fake/")
    assert result["transaction"]["id"] == "tx_1"
    assert result["transaction"]["success"] is True


def test_charge_returns_structured_error_on_http_error():
    body = json.dumps({
        "credit_card": {
            "code": "card-declined",
            "name": "La carte de crédit a été déclinée.",
        }
    })
    err = HTTPError(
        url="http://fake/", code=422, msg="", hdrs=None,
        fp=MagicMock(read=MagicMock(return_value=body.encode("utf-8"))),
    )
    err.read = lambda: body.encode("utf-8")
    with patch("inf349.clients.payment.urlopen", side_effect=err):
        result = charge(33.0, VALID_CARD, url="http://fake/")
    assert result["credit_card"]["code"] == "card-declined"


def test_charge_raises_on_network_error():
    with patch("inf349.clients.payment.urlopen", side_effect=URLError("boom")):
        with pytest.raises(PaymentClientError) as exc:
            charge(33.0, VALID_CARD, url="http://fake/")
    assert exc.value.code == "payment-unreachable"


def test_charge_raises_on_invalid_json():
    with patch(
        "inf349.clients.payment.urlopen",
        return_value=_mock_context("not json"),
    ):
        with pytest.raises(PaymentClientError):
            charge(33.0, VALID_CARD, url="http://fake/")
