import json
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT = 10


class PaymentClientError(Exception):
    """Raised when the remote payment service cannot be reached or parsed.

    This is distinct from a structured error returned by the remote service
    (card declined, invalid number, etc.) which is expressed inside the JSON
    payload and must be relayed to the caller unchanged.
    """

    def __init__(self, code: str, name: str):
        super().__init__(name)
        self.code = code
        self.name = name


def charge(amount_charged: float, credit_card: Dict, url: str,
           timeout: float = DEFAULT_TIMEOUT) -> Dict:
    """POST a charge request to the remote payment service.

    Returns the parsed JSON body regardless of success or structured failure
    (the remote encodes declines / invalid data inside the body under the
    `credit_card` key).

    Raises PaymentClientError on network, transport or JSON parsing failures.
    """
    body = json.dumps({
        "credit_card": credit_card,
        "amount_charged": amount_charged,
    }).encode("utf-8")

    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as err:
        # The remote returned a non-2xx but the body may still carry a
        # structured error we want to relay unchanged.
        try:
            raw = err.read().decode("utf-8")
            return json.loads(raw)
        except (ValueError, OSError) as parse_err:
            raise PaymentClientError(
                "payment-unreachable",
                f"Réponse invalide du service de paiement ({err.code})",
            ) from parse_err
    except (URLError, OSError) as exc:
        raise PaymentClientError(
            "payment-unreachable",
            "Le service de paiement est indisponible",
        ) from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PaymentClientError(
            "payment-unreachable",
            "Réponse invalide du service de paiement",
        ) from exc
