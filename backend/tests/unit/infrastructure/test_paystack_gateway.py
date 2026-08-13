"""The Paystack adapter's HTTP translation, proven against a mocked transport.

`httpx.MockTransport` intercepts at the transport layer, so everything above it — URL
construction, headers, JSON encoding, response unwrapping, error mapping — is the real
adapter code production runs. No test here (or anywhere) talks to api.paystack.co.
"""

import json

import httpx
import pytest

from ugjcs.infrastructure.payments.paystack import PaystackError, PaystackGateway

SECRET = "sk_test_secret_value"  # a fixture shaped like a key, not a credential


def gateway_answering(response: httpx.Response, seen: list[httpx.Request]) -> PaystackGateway:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response

    return PaystackGateway(SECRET, transport=httpx.MockTransport(handler))


async def test_initialize_sends_amount_email_reference_and_returns_the_checkout_url() -> None:
    seen: list[httpx.Request] = []
    gateway = gateway_answering(
        httpx.Response(
            200,
            json={
                "status": True,
                "message": "Authorization URL created",
                "data": {"authorization_url": "https://checkout.paystack.com/abc123"},
            },
        ),
        seen,
    )
    url = await gateway.initialize_transaction(
        email="author@sdj.test", amount_minor_units=15000, reference="ref-1"
    )
    assert url == "https://checkout.paystack.com/abc123"
    [request] = seen
    assert str(request.url) == "https://api.paystack.co/transaction/initialize"
    assert request.headers["Authorization"] == f"Bearer {SECRET}"
    body = json.loads(request.content)
    assert body == {
        "email": "author@sdj.test",
        "amount": 15000,  # pesewas straight through: no unit conversion exists to get wrong
        "currency": "GHS",
        "reference": "ref-1",
    }


async def test_verify_is_true_only_for_a_successful_charge() -> None:
    for paystack_status, expected in (("success", True), ("failed", False), ("abandoned", False)):
        seen: list[httpx.Request] = []
        gateway = gateway_answering(
            httpx.Response(
                200,
                json={"status": True, "message": "ok", "data": {"status": paystack_status}},
            ),
            seen,
        )
        assert await gateway.verify_transaction("ref-2") is expected
        assert str(seen[0].url) == "https://api.paystack.co/transaction/verify/ref-2"


async def test_a_refusal_raises_without_leaking_the_secret() -> None:
    gateway = gateway_answering(
        httpx.Response(401, json={"status": False, "message": "Invalid key"}), []
    )
    with pytest.raises(PaystackError) as excinfo:
        await gateway.initialize_transaction(
            email="author@sdj.test", amount_minor_units=15000, reference="ref-3"
        )
    assert "Invalid key" in str(excinfo.value)
    assert SECRET not in str(excinfo.value)


async def test_a_response_without_an_authorization_url_raises() -> None:
    gateway = gateway_answering(
        httpx.Response(200, json={"status": True, "message": "ok", "data": {}}), []
    )
    with pytest.raises(PaystackError):
        await gateway.initialize_transaction(
            email="author@sdj.test", amount_minor_units=15000, reference="ref-4"
        )


def test_the_repr_never_contains_the_secret() -> None:
    """A stack trace or debugger dump of the gateway must be safe to paste anywhere."""
    assert SECRET not in repr(PaystackGateway(SECRET))
