"""One-shot wipe of old-brand demo data, run once per boot between migrate and seed.

The deployed database predates the rebrand to the Science and Development Journal (SDJ):
its judge accounts live under `@ugjcs.test` addresses and its manuscripts carry
`UGJCS-2026-NNNN` tracking codes, neither of which the rebranded application will ever
mint or accept again. Rather than rewriting rows in place — tracking codes are baked into
the hash-chained editorial event payloads, so an in-place rename would falsify the audit
trail it exists to protect — this script deletes every row from every application table
in one transaction, and lets the `seed_demo --if-empty` step that follows it in
`entrypoint.sh` recreate the whole corpus fresh under the new brand.

The wipe is gated on a canary, not run unconditionally: only if some user's email ends in
`@ugjcs.test` (an address only the old-brand seed ever created) is there anything to
erase. Once the rebranded seed has run, no such user exists, so every subsequent boot
prints "no old-brand data" and moves straight on — the script is a permanent, idempotent
resident of the entrypoint, not a migration that must be removed after one deploy.

Deleting editorial events requires disabling the `editorial_events_append_only` trigger
for the duration of the transaction — the same loudly-stated, owner-level administrative
manoeuvre `prune_junk.py` documents, and like it, reachable only from the container
entrypoint, never from any application code path.

Documents the old corpus uploaded to S3 are deliberately left behind: their keys are
derived from manuscript UUIDs the new seed will never mint again, so the orphaned objects
are unreachable through the application. Accepting a few stray demo PDFs in the bucket is
cheaper and safer than giving this script S3 credentials and delete permissions.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine

_OLD_BRAND_EMAIL_SUFFIX = "@ugjcs.test"

# Every application table, ordered so each is emptied before any table it references:
# child tables (foreign-key holders) first, then manuscripts and users last.
_WIPE_ORDER: tuple[str, ...] = (
    "editorial_events",
    "review_assignments",
    "apc_invoices",
    "manuscript_authors",
    "manuscripts",
    "refresh_tokens",
    "user_roles",
    "users",
)


async def wipe_if_old_brand(engine: AsyncEngine) -> bool:
    """Delete all rows from all app tables if the old-brand canary is present.

    Returns True if a wipe happened, False if the database was already on the new brand.
    """
    async with engine.begin() as conn:
        canary = (
            await conn.execute(
                text("SELECT count(*) FROM users WHERE email LIKE :pattern"),
                {"pattern": f"%{_OLD_BRAND_EMAIL_SUFFIX}"},
            )
        ).scalar_one()
        if canary == 0:
            print("Rebrand wipe: no old-brand data.")
            return False
        print(
            f"Rebrand wipe: found {canary} old-brand account(s); "
            "clearing all application tables for reseed under the new brand."
        )
        await conn.execute(
            text("ALTER TABLE editorial_events DISABLE TRIGGER editorial_events_append_only")
        )
        for table in _WIPE_ORDER:
            result = await conn.execute(text(f"DELETE FROM {table}"))
            print(f"Rebrand wipe: cleared {table} ({result.rowcount} row(s)).")
        await conn.execute(
            text("ALTER TABLE editorial_events ENABLE TRIGGER editorial_events_append_only")
        )
        print("Rebrand wipe: done; seed_demo will recreate the corpus.")
        return True


async def run() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    try:
        await wipe_if_old_brand(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
