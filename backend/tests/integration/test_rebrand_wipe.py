"""The rebrand wipe clears everything when the old-brand canary is present — and
touches nothing when it is not — while leaving the append-only guard armed.

Regression companion to the SDJ rebrand: the deployed database still held the
pre-rebrand corpus (`@ugjcs.test` accounts, `UGJCS-2026-NNNN` codes), which the
rebranded application can no longer mint or accept, so the entrypoint wipes it once
and lets `seed_demo --if-empty` rebuild the corpus under the new brand.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.engine import session_factory
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository
from ugjcs.scripts.rebrand_wipe import _WIPE_ORDER, wipe_if_old_brand

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 13, 2, 0, tzinfo=UTC)


async def _store_user(engine: AsyncEngine, *, email: str) -> UserId:
    user_id = UserId(uuid4())
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, full_name, affiliation,"
                " expertise, reviewer_capacity, is_verified, is_active)"
                " VALUES (:id, :email, 'x', 'Test User', 'Test U', '{}', 3, true, true)"
            ),
            {"id": user_id, "email": email},
        )
    return user_id


async def _store_manuscript(engine: AsyncEngine, *, author: UserId) -> Manuscript:
    factory = session_factory(engine)
    async with factory() as session:
        manuscript = Manuscript(
            id=ManuscriptId(uuid4()),
            tracking_code=TrackingCode.mint(2026, 9001),
            title="A manuscript from before the rebrand",
            abstract="An abstract long enough to be plausible.",
            keywords=("test",),
            author_ids=(author,),
            corresponding_author_id=author,
        )
        manuscript.submit(actor_id=author, occurred_at=NOW)
        repository = SqlAlchemyManuscriptRepository(session)
        await repository.add(manuscript)
        await session.commit()
        return manuscript


async def _row_counts(engine: AsyncEngine) -> dict[str, int]:
    async with engine.connect() as conn:
        counts: dict[str, int] = {}
        for table in _WIPE_ORDER:
            counts[table] = (
                await conn.execute(text(f"SELECT count(*) FROM {table}"))
            ).scalar_one()
        return counts


async def test_the_canary_triggers_a_full_wipe_of_every_app_table(engine: AsyncEngine) -> None:
    old_brand_author = await _store_user(engine, email="author@ugjcs.test")
    await _store_manuscript(engine, author=old_brand_author)

    wiped = await wipe_if_old_brand(engine)

    assert wiped is True
    assert all(count == 0 for count in (await _row_counts(engine)).values())


async def test_a_new_brand_database_is_left_untouched(engine: AsyncEngine) -> None:
    new_brand_author = await _store_user(engine, email="author@sdj.test")
    manuscript = await _store_manuscript(engine, author=new_brand_author)

    wiped = await wipe_if_old_brand(engine)

    assert wiped is False
    async with engine.connect() as conn:
        remaining = (
            (await conn.execute(text("SELECT tracking_code FROM manuscripts"))).scalars().all()
        )
    assert remaining == [manuscript.tracking_code.value]


async def test_the_wipe_leaves_the_append_only_trigger_enabled(engine: AsyncEngine) -> None:
    old_brand_author = await _store_user(engine, email="eic@ugjcs.test")
    await _store_manuscript(engine, author=old_brand_author)
    await wipe_if_old_brand(engine)

    survivor_author = await _store_user(engine, email="author@sdj.test")
    survivor = await _store_manuscript(engine, author=survivor_author)
    async with engine.connect() as conn:
        with pytest.raises(DBAPIError, match="append-only"):
            await conn.execute(
                text("DELETE FROM editorial_events WHERE manuscript_id = :id"),
                {"id": survivor.id},
            )
