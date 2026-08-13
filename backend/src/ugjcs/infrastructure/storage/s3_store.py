"""S3-backed `DocumentStore`.

`boto3` is synchronous. Every method here runs the blocking call in a worker thread via
`asyncio.to_thread`, so the adapter satisfies the async `DocumentStore` protocol without
blocking the event loop for the duration of an S3 round trip. `boto3` is imported nowhere
outside this package — the domain and application layers never see it.
"""

import asyncio
from datetime import timedelta

import boto3  # type: ignore[import-untyped]


class S3DocumentStore:
    """Talks to exactly one bucket, which has all public access blocked at the bucket
    level (see `infra/s3.tf`). Every read a caller of this adapter ever performs goes
    through a pre-signed URL generated on demand here; nothing is ever proxied through
    the API process, and nothing is ever made public via a bucket policy."""

    def __init__(self, *, bucket: str, region: str) -> None:
        self._bucket = bucket
        self._client = boto3.client("s3", region_name=region)

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> bytes:
        """Read an object's bytes back — used only by full-text extraction at publish
        time and the entrypoint backfill, never to proxy a download to a reader (that
        stays `presigned_url`'s job). Raises `LookupError` for a missing key, per the
        `DocumentStore` port, so callers never learn this adapter speaks boto3."""

        def _read() -> bytes:
            try:
                response = self._client.get_object(Bucket=self._bucket, Key=key)
            except self._client.exceptions.NoSuchKey as error:
                raise LookupError(f"no stored document under key {key!r}") from error
            body: bytes = response["Body"].read()
            return body

        return await asyncio.to_thread(_read)

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=int(expires_in.total_seconds()),
        )
        return url
