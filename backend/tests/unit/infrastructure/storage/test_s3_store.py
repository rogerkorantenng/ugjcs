"""Unit tests for the S3 adapter, against a mocked `boto3` client.

No network call, no AWS credentials, no Docker: `boto3.client(...)` construction itself
never talks to AWS, and every method that would is replaced here with a `Mock`. Real
behaviour against a live bucket is proven by the deployment's live verification, not by
this suite — this suite proves the adapter calls `boto3` the way it should.
"""

from datetime import timedelta
from unittest.mock import MagicMock

import pytest

from ugjcs.infrastructure.storage.s3_store import S3DocumentStore


@pytest.fixture
def store_and_client() -> tuple[S3DocumentStore, MagicMock]:
    store = S3DocumentStore(bucket="ugjcs-manuscripts-test", region="us-east-1")
    mock_client = MagicMock()
    store._client = mock_client
    return store, mock_client


async def test_put_writes_to_the_configured_bucket_with_the_given_key_and_content_type(
    store_and_client: tuple[S3DocumentStore, MagicMock],
) -> None:
    store, client = store_and_client
    await store.put("manuscripts/x/v1/original.pdf", b"%PDF-1.4...", content_type="application/pdf")
    client.put_object.assert_called_once_with(
        Bucket="ugjcs-manuscripts-test",
        Key="manuscripts/x/v1/original.pdf",
        Body=b"%PDF-1.4...",
        ContentType="application/pdf",
    )


async def test_presigned_url_requests_a_get_and_returns_the_generated_url(
    store_and_client: tuple[S3DocumentStore, MagicMock],
) -> None:
    store, client = store_and_client
    client.generate_presigned_url.return_value = "https://s3.example/signed"
    url = await store.presigned_url(
        "manuscripts/x/v1/original.pdf", expires_in=timedelta(minutes=5)
    )
    assert url == "https://s3.example/signed"
    client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "ugjcs-manuscripts-test", "Key": "manuscripts/x/v1/original.pdf"},
        ExpiresIn=300,
    )
