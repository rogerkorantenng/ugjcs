"""Remove non-corpus manuscripts left behind by live end-to-end verification.

Running QA against the deployed system is done through the real UI, so every sweep
leaves real manuscripts behind — and one of them ended up PUBLISHED, sitting in the
public archive next to the curated corpus. This script deletes every manuscript whose
tracking code is not in the seeded corpus, together with its authors rows, review
assignments and editorial events.

Deleting editorial events requires disabling the `editorial_events_append_only` trigger
for the duration of one transaction. That is exactly the kind of privileged operation
the tamper-evident design is meant to make loud, so it is stated here rather than
hidden: this is an owner-level administrative prune of demonstration data, run from the
container entrypoint (the only place with database access), not an application code
path. Nothing in the API can reach it.

The corpus allowlist is derived from `seed_demo.MANUSCRIPT_SPECS`, so a manuscript
added to the seed later is automatically protected without touching this script.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.domain.ids import TrackingCode
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.engine import create_engine
from ugjcs.scripts.seed_demo import MANUSCRIPT_SPECS, SEED_TRACKING_YEAR


def corpus_allowlist() -> tuple[str, ...]:
    """Tracking codes of the seeded corpus, minted through the same `TrackingCode`
    the seed itself uses, so a rebrand of the code format can never strand this list
    on a stale prefix."""
    return tuple(
        TrackingCode.mint(SEED_TRACKING_YEAR, spec.sequence).value for spec in MANUSCRIPT_SPECS
    )


async def prune(engine: AsyncEngine) -> int:
    """Delete every manuscript outside the corpus allowlist; return how many."""
    allow = list(corpus_allowlist())
    async with engine.begin() as conn:
        junk = (
            await conn.execute(
                text(
                    "SELECT id, tracking_code FROM manuscripts WHERE tracking_code != ALL(:allow)"
                ),
                {"allow": allow},
            )
        ).all()
        if not junk:
            print("Prune: no non-corpus manuscripts found.")
            return 0
        ids = [row.id for row in junk]
        for row in junk:
            print(f"Prune: removing {row.tracking_code}")
        await conn.execute(
            text("ALTER TABLE editorial_events DISABLE TRIGGER editorial_events_append_only")
        )
        await conn.execute(
            text("DELETE FROM editorial_events WHERE manuscript_id = ANY(:ids)"), {"ids": ids}
        )
        await conn.execute(
            text("ALTER TABLE editorial_events ENABLE TRIGGER editorial_events_append_only")
        )
        await conn.execute(
            text("DELETE FROM review_assignments WHERE manuscript_id = ANY(:ids)"), {"ids": ids}
        )
        await conn.execute(
            text("DELETE FROM manuscript_authors WHERE manuscript_id = ANY(:ids)"), {"ids": ids}
        )
        await conn.execute(text("DELETE FROM manuscripts WHERE id = ANY(:ids)"), {"ids": ids})
        print(f"Prune: removed {len(ids)} manuscript(s); corpus of {len(allow)} untouched.")
        return len(ids)


async def run() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    try:
        await prune(engine)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
