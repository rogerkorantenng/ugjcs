"""Paystack-backed `PaymentGateway`.

The secret key's whole lifecycle inside this process is: read from configuration,
held on this adapter, written into an `Authorization` header. It is never logged,
never interpolated into an exception message, and `__repr__` is overridden so a
stack trace or debugger dump of this object cannot leak it either. `httpx` is
imported nowhere outside this package — the application layer sees only the port.
"""

from typing import Any

import httpx

_BASE_URL = "https://api.paystack.co"
_TIMEOUT_SECONDS = 20.0


class PaystackError(Exception):
    """Paystack refused, failed, or answered with a shape this adapter cannot read.

    Messages carry Paystack's own error text and HTTP status — never the request
    headers, which is where the secret lives.
    """


class PaystackGateway:
    def __init__(self, secret_key: str, *, transport: httpx.AsyncBaseTransport | None = None):
        self._secret_key = secret_key
        # Injectable transport so unit tests mock Paystack at the HTTP layer
        # (`httpx.MockTransport`) and prove the real request/response translation,
        # not a stub of this class. Production callers never pass it.
        self._transport = transport

    def __repr__(self) -> str:
        return "PaystackGateway(secret_key=<redacted>)"

    async def initialize_transaction(
        self, *, email: str, amount_minor_units: int, reference: str
    ) -> str:
        """POST /transaction/initialize; return the checkout `authorization_url`.

        The reference is ours, passed to Paystack rather than taking theirs back:
        verification is then keyed by something this system minted and stored before
        any network call happened, so a crash between initialize and respond loses
        nothing.
        """
        data = await self._call(
            "POST",
            "/transaction/initialize",
            json={
                "email": email,
                # Paystack takes minor units (pesewas for GHS) — the same unit the
                # invoice stores, so no conversion (and no conversion bug) exists.
                "amount": amount_minor_units,
                "currency": "GHS",
                "reference": reference,
            },
        )
        url = data.get("authorization_url")
        if not isinstance(url, str) or not url:
            raise PaystackError("initialize response carried no authorization_url")
        return url

    async def verify_transaction(self, reference: str) -> bool:
        """GET /transaction/verify/{reference}; True only for a settled, successful charge."""
        data = await self._call("GET", f"/transaction/verify/{reference}")
        return data.get("status") == "success"

    async def _call(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """One authenticated round trip, unwrapped to Paystack's `data` payload."""
        try:
            async with httpx.AsyncClient(
                base_url=_BASE_URL,
                timeout=_TIMEOUT_SECONDS,
                transport=self._transport,
                headers={"Authorization": f"Bearer {self._secret_key}"},
            ) as client:
                response = await client.request(method, path, json=json)
        except httpx.HTTPError as error:
            # str(error) on httpx errors names the URL and failure, not the headers.
            raise PaystackError(f"could not reach Paystack: {error}") from error
        body = self._parse(response)
        if response.status_code >= 400 or body.get("status") is not True:
            message = body.get("message", "no message")
            raise PaystackError(f"Paystack answered {response.status_code}: {message}")
        data = body.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _parse(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as error:
            raise PaystackError(
                f"Paystack answered {response.status_code} with a non-JSON body"
            ) from error
        return body if isinstance(body, dict) else {}
