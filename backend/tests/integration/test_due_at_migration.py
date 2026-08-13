"""`0006_review_due_dates` proven against the real Alembic scripts, not the metadata.

`test_migration_parity.py` asserts the *shape* the metadata-built schema and the
migration must agree on; it can say nothing about the migration's data step, because the
integration fixtures build their schema with `Base.metadata.create_all` and never run
Alembic at all. The backfill — every pre-existing assignment gets
`assigned_at + 21 days` — only exists inside the migration script, so the only honest
way to test it is: upgrade to 0005, plant a row the way a pre-deadline deploy would
have, then upgrade to head and look.

Alembic runs in a subprocess (the same `python -m alembic upgrade` the container's
entrypoint runs) rather than in-process through its API: `alembic/env.py` reads settings
at import time through the process-wide `get_settings()` cache, and poking a different
database URL into a cache the rest of this test session shares is exactly the kind of
cross-test bleed the subprocess boundary makes impossible.
"""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from ugjcs.infrastructure.db.engine import create_engine

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[2]
ASSIGNED_AT = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)


def _alembic(postgres_url: str, *args: str) -> None:
    """Run `alembic <args>` against the test container, loudly on failure."""
    env = os.environ | {
        "UGJCS_DATABASE_URL": postgres_url,
        # Required by `Settings` (no default, correctly); unused by migrations.
        "UGJCS_JWT_SECRET": "migration-test-secret",
    }
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"alembic {' '.join(args)} failed:\n{completed.stdout}\n{completed.stderr}"
    )


async def _reset_schema(engine: AsyncEngine) -> None:
    """A truly blank slate — including `alembic_version`, which `Base.metadata` knows
    nothing about — so this test neither inherits another test's tables nor leaks its
    own migration state into the fixtures that build schemas from metadata."""
    async with engine.begin() as connection:
        await connection.exec_driver_sql("DROP SCHEMA public CASCADE")
        await connection.exec_driver_sql("CREATE SCHEMA public")


async def test_upgrading_to_head_backfills_due_at_from_assigned_at(postgres_url: str) -> None:
    engine = create_engine(postgres_url, echo=False)
    try:
        await _reset_schema(engine)
        # The world as a pre-deadline deploy left it: schema at 0005, one assignment
        # recorded with no due date because the column did not exist yet.
        _alembic(postgres_url, "upgrade", "0005")
        manuscript_id = uuid4()
        async with engine.begin() as connection:
            await connection.exec_driver_sql(
                "INSERT INTO manuscripts (id, tracking_code, title, abstract, keywords, "
                "corresponding_author_id, status, version, minimum_reviews, submitted_reviews) "
                f"VALUES ('{manuscript_id}', 'SDJ-2026-0901', 'T', 'A.', '{{}}', "
                f"'{uuid4()}', 'under_review', 1, 2, 0)"
            )
            await connection.exec_driver_sql(
                "INSERT INTO review_assignments (id, manuscript_id, reviewer_id, status, "
                f"assigned_at) VALUES ('{uuid4()}', '{manuscript_id}', '{uuid4()}', "
                f"'assigned', '{ASSIGNED_AT.isoformat()}')"
            )

        _alembic(postgres_url, "upgrade", "head")

        async with engine.connect() as connection:
            result = await connection.exec_driver_sql(
                "SELECT assigned_at, due_at FROM review_assignments"
            )
            [(assigned_at, due_at)] = result.fetchall()
        assert due_at == assigned_at + timedelta(days=21)
        assert due_at == ASSIGNED_AT + timedelta(days=21)
    finally:
        await _reset_schema(engine)
        await engine.dispose()


async def test_downgrading_one_step_drops_due_at_cleanly(postgres_url: str) -> None:
    """The reversibility half: `downgrade 0005` must leave a schema 0005 itself could
    have produced, or the migration is a one-way door mislabelled as reversible."""
    engine = create_engine(postgres_url, echo=False)
    try:
        await _reset_schema(engine)
        _alembic(postgres_url, "upgrade", "head")
        _alembic(postgres_url, "downgrade", "0005")
        async with engine.connect() as connection:
            result = await connection.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'review_assignments' AND column_name = 'due_at'"
            )
            assert result.fetchall() == []
    finally:
        await _reset_schema(engine)
        await engine.dispose()
