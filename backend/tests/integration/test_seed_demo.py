"""Integration coverage for the demo seed script's document handling.

Runs against a real PostgreSQL container (see `conftest.postgres_url`) with a fake
`DocumentStore` standing in for S3 — exactly the substitution the task's own guidance
calls for, since this machine has no route to the bucket the way the running container
does. What this proves that `make check`'s unit suite cannot: that `seed_demo.run()`
actually persists document keys through a full session/unit-of-work cycle, and that
running it twice — the fate of every container restart — neither re-uploads a document
nor creates a duplicate manuscript.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import timedelta
from io import BytesIO

import pytest
from pypdf import PdfReader

from ugjcs.domain.ids import TrackingCode
from ugjcs.infrastructure.config import get_settings
from ugjcs.infrastructure.db.base import Base
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.models import EditorialEventRow  # noqa: F401  register tables
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.scripts import seed_demo

pytestmark = pytest.mark.integration


@dataclass
class FakeDocumentStore:
    """Records every write, so a test can assert a second seed run makes none."""

    objects: dict[str, bytes] = field(default_factory=dict)
    put_calls: list[str] = field(default_factory=list)

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        self.objects[key] = data
        self.put_calls.append(key)

    async def presigned_url(self, key: str, *, expires_in: timedelta) -> str:
        return f"https://fake-s3.test/{key}"


@pytest.fixture(autouse=True)
async def _fresh_database(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[None]:
    """Point `Settings` at the shared container and give this test a clean schema.

    `seed_demo.run` builds its own engine from `get_settings()` rather than accepting one
    as an argument — that is how the entrypoint script actually calls it — so the only way
    to redirect it here is the same environment variable the container sets.
    """
    monkeypatch.setenv("UGJCS_DATABASE_URL", postgres_url)
    monkeypatch.setenv("UGJCS_JWT_SECRET", "integration-test-secret-value")
    get_settings.cache_clear()

    engine = create_engine(postgres_url, echo=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield
    get_settings.cache_clear()


async def _uow() -> SqlAlchemyUnitOfWork:
    engine = create_engine(get_settings().database_url, echo=False)
    return SqlAlchemyUnitOfWork(session_factory(engine))


async def test_every_seeded_manuscript_ends_up_with_both_document_keys_in_the_store() -> None:
    store = FakeDocumentStore()
    await seed_demo.run(only_if_empty=False, documents=store)

    async with await _uow() as uow:
        for spec in seed_demo.MANUSCRIPT_SPECS:
            code = TrackingCode.mint(seed_demo.SEED_TRACKING_YEAR, spec.sequence)
            manuscript = await uow.manuscripts.get_by_tracking_code(code)
            assert manuscript is not None, f"manuscript {code.value} was not created"
            assert manuscript.original_document_key is not None
            assert manuscript.anonymised_document_key is not None
            assert manuscript.original_document_key in store.objects
            assert manuscript.anonymised_document_key in store.objects
            assert store.objects[manuscript.original_document_key].startswith(b"%PDF")
            assert store.objects[manuscript.anonymised_document_key].startswith(b"%PDF")


async def test_rerunning_the_seed_creates_no_manuscripts_and_uploads_no_documents_twice() -> None:
    store = FakeDocumentStore()
    await seed_demo.run(only_if_empty=False, documents=store)
    first_run_puts = list(store.put_calls)
    first_run_object_count = len(store.objects)

    await seed_demo.run(only_if_empty=False, documents=store)

    assert store.put_calls == first_run_puts
    assert len(store.objects) == first_run_object_count

    async with await _uow() as uow:
        for spec in seed_demo.MANUSCRIPT_SPECS:
            code = TrackingCode.mint(seed_demo.SEED_TRACKING_YEAR, spec.sequence)
            assert await uow.manuscripts.get_by_tracking_code(code) is not None


async def test_the_if_empty_fast_path_still_backfills_documents_a_prior_run_left_missing() -> None:
    """Simulates redeploying this feature onto a database an earlier, document-less
    seed script already fully populated: `--if-empty` must not mistake a fully PUBLISHED,
    document-less corpus for nothing left to do.
    """
    store = FakeDocumentStore()
    await seed_demo.run(only_if_empty=False, documents=store)

    async with await _uow() as uow:
        last_code = TrackingCode.mint(seed_demo.SEED_TRACKING_YEAR, seed_demo._LAST_SEQUENCE)
        manuscript = await uow.manuscripts.get_by_tracking_code(last_code)
        assert manuscript is not None
        manuscript.original_document_key = None
        manuscript.anonymised_document_key = None
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    store.objects.clear()
    store.put_calls.clear()
    await seed_demo.run(only_if_empty=True, documents=store)

    async with await _uow() as uow:
        manuscript = await uow.manuscripts.get_by_tracking_code(last_code)
        assert manuscript is not None
        assert manuscript.original_document_key is not None
        assert manuscript.anonymised_document_key is not None


async def test_the_authors_original_carries_their_name_and_the_reviewers_copy_does_not() -> None:
    store = FakeDocumentStore()
    await seed_demo.run(only_if_empty=False, documents=store)

    spec = seed_demo.MANUSCRIPT_SPECS[0]
    author_name = seed_demo._AUTHOR_NAME_BY_EMAIL[spec.corresponding_author_email]

    async with await _uow() as uow:
        code = TrackingCode.mint(seed_demo.SEED_TRACKING_YEAR, spec.sequence)
        manuscript = await uow.manuscripts.get_by_tracking_code(code)
        assert manuscript is not None
        assert manuscript.original_document_key is not None
        assert manuscript.anonymised_document_key is not None
        original = store.objects[manuscript.original_document_key]
        anonymised = store.objects[manuscript.anonymised_document_key]

    original_metadata = PdfReader(BytesIO(original)).metadata
    anonymised_metadata = PdfReader(BytesIO(anonymised)).metadata
    assert original_metadata is not None
    assert original_metadata.author == author_name
    assert original_metadata.creator == author_name
    assert anonymised_metadata is not None
    assert anonymised_metadata.author is None
    assert anonymised_metadata.creator is None
