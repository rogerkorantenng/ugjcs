"""Integration fixtures. One PostgreSQL container per test session."""

from collections.abc import AsyncIterator, Iterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.postgres import PostgresContainer

from ugjcs.infrastructure.db.base import Base
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.models import EditorialEventRow  # noqa: F401  register tables

APPEND_ONLY_FUNCTION = """
CREATE OR REPLACE FUNCTION ugjcs_reject_event_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'editorial_events is append-only; % rejected', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""

APPEND_ONLY_TRIGGER = """
CREATE TRIGGER editorial_events_append_only
    BEFORE UPDATE OR DELETE ON editorial_events
    FOR EACH ROW EXECUTE FUNCTION ugjcs_reject_event_mutation();
"""

NO_TRUNCATE_TRIGGER = """
CREATE TRIGGER editorial_events_no_truncate
    BEFORE TRUNCATE ON editorial_events
    FOR EACH STATEMENT EXECUTE FUNCTION ugjcs_reject_event_mutation();
"""


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        yield container.get_connection_url()


@pytest.fixture
async def session(postgres_url: str) -> AsyncIterator[AsyncSession]:
    """A clean schema per test, with the append-only trigger installed."""
    engine = create_engine(postgres_url, echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
        await connection.exec_driver_sql(APPEND_ONLY_FUNCTION)
        await connection.exec_driver_sql(APPEND_ONLY_TRIGGER)
        await connection.exec_driver_sql(NO_TRUNCATE_TRIGGER)
    factory = session_factory(engine)
    async with factory() as session:
        yield session
    await engine.dispose()
