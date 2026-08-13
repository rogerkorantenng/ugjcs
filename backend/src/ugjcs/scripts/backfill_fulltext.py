"""Backfill `manuscripts.fulltext` for papers published before the search feature.

Runs from the container entrypoint after migrate/seed/prune, every boot. Idempotent by
selection, the same pattern `0006`'s backfill used: only rows where `fulltext IS NULL`
are candidates, so a second run (or a boot after everything is indexed) selects nothing
and exits — and a paper whose extraction genuinely failed is retried next boot rather
than marked done, which is the honest behaviour for a transient S3 error.

Failures are contained per manuscript on purpose. The entrypoint runs under `set -eu`,
so an unhandled exception here would keep the API from ever starting; one paper with a
corrupt PDF (or a missing S3 object) must cost that paper its search entry, not the
whole deployment its uptime. Extraction that yields no text at all leaves the row NULL
— storing an empty string would only stop the retry while adding nothing searchable.

The store is a parameter (any `DocumentStore`) so the integration test can drive this
against an in-memory fake; only `run()` commits to S3.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.application.ports import DocumentStore
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine
from ugjcs.infrastructure.storage.fulltext import extract_pdf_text
from ugjcs.infrastructure.storage.s3_store import S3DocumentStore


async def backfill(engine: AsyncEngine, store: DocumentStore) -> int:
    """Index every published, un-indexed manuscript; return how many were indexed."""
    async with engine.begin() as conn:
        pending = (
            await conn.execute(
                text(
                    "SELECT id, tracking_code, original_document_key FROM manuscripts "
                    "WHERE status = 'published' AND fulltext IS NULL "
                    "AND original_document_key IS NOT NULL"
                )
            )
        ).all()
    if not pending:
        print("Fulltext backfill: nothing to index.")
        return 0
    indexed = 0
    for row in pending:
        try:
            body = extract_pdf_text(await store.get(row.original_document_key))
        except Exception as error:  # deliberately broad - one bad PDF must not stop the boot
            print(f"Fulltext backfill: skipping {row.tracking_code}: {error}")
            continue
        if not body:
            print(f"Fulltext backfill: {row.tracking_code} yielded no extractable text.")
            continue
        # One transaction per manuscript: a crash mid-backfill keeps everything
        # already indexed, and the NULL filter above resumes exactly where it stopped.
        async with engine.begin() as conn:
            await conn.execute(
                text("UPDATE manuscripts SET fulltext = :body WHERE id = :id"),
                {"body": body, "id": row.id},
            )
        indexed += 1
        print(f"Fulltext backfill: indexed {row.tracking_code} ({len(body)} chars).")
    print(f"Fulltext backfill: indexed {indexed} of {len(pending)} candidate(s).")
    return indexed


async def run() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    store = S3DocumentStore(bucket=settings.s3_bucket_name, region=settings.aws_region)
    try:
        await backfill(engine, store)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
