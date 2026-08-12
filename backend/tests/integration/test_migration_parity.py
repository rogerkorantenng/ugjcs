"""The migration and the metadata must produce the same schema.

Integration tests build the schema from `Base.metadata`; production builds it with Alembic.
Nothing forces those to agree, so this test asserts it explicitly.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration

EXPECTED_TABLES = {"editorial_events", "manuscript_authors", "manuscripts"}


async def test_the_expected_tables_exist(session: AsyncSession) -> None:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    assert {row[0] for row in result} >= EXPECTED_TABLES


async def test_the_append_only_triggers_are_installed(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT tgname FROM pg_trigger "
            "WHERE tgrelid = 'editorial_events'::regclass AND NOT tgisinternal"
        )
    )
    names = {row[0] for row in result}
    assert "editorial_events_append_only" in names
    assert "editorial_events_no_truncate" in names


async def test_the_event_primary_key_is_manuscript_and_sequence(session: AsyncSession) -> None:
    result = await session.execute(
        text(
            "SELECT a.attname FROM pg_index i "
            "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
            "WHERE i.indrelid = 'editorial_events'::regclass AND i.indisprimary"
        )
    )
    assert {row[0] for row in result} == {"manuscript_id", "sequence"}


async def test_tracking_code_has_a_unique_index_not_a_unique_constraint(
    session: AsyncSession,
) -> None:
    """models.py declares unique=True, index=True, which SQLAlchemy compiles to a bare unique

    INDEX, not a table constraint. A migration that instead created a UniqueConstraint would
    produce a different catalogue object under a name that looks identical — this is exactly
    the drift the Task 3 implementer caught by hand before the migration was authored.
    """
    index = await session.execute(
        text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE tablename = 'manuscripts' AND indexname = 'ix_manuscripts_tracking_code'"
        )
    )
    rows = index.fetchall()
    assert len(rows) == 1
    assert "UNIQUE" in rows[0][0]

    constraint = await session.execute(
        text(
            "SELECT conname FROM pg_constraint "
            "WHERE conrelid = 'manuscripts'::regclass AND contype = 'u' "
            "AND conname = 'ix_manuscripts_tracking_code'"
        )
    )
    assert constraint.first() is None


async def test_document_key_columns_exist_and_are_nullable(session: AsyncSession) -> None:
    """Manually cross-checked against `alembic upgrade head` on a throwaway container as
    part of writing `0004_manuscript_document_keys.py` — this asserts the same shape
    `to_row`/`to_domain` depend on, the same way the rest of this file does."""
    result = await session.execute(
        text(
            "SELECT column_name, is_nullable, character_maximum_length "
            "FROM information_schema.columns WHERE table_name = 'manuscripts' "
            "AND column_name IN ('original_document_key', 'anonymised_document_key')"
        )
    )
    columns = {row[0]: (row[1], row[2]) for row in result}
    assert columns == {
        "original_document_key": ("YES", 512),
        "anonymised_document_key": ("YES", 512),
    }
