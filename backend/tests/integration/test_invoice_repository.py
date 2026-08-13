"""`SqlAlchemyApcInvoiceRepository` against a live PostgreSQL."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import DEFAULT_APC_PESEWAS
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.invoice_repository import SqlAlchemyApcInvoiceRepository
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)


async def _seed_manuscript(session: AsyncSession, sequence: int) -> Manuscript:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )
    await repository.add(manuscript)
    await session.commit()
    return manuscript


async def test_create_if_absent_opens_one_pending_invoice_and_only_one(
    session: AsyncSession,
) -> None:
    manuscript = await _seed_manuscript(session, 601)
    invoices = SqlAlchemyApcInvoiceRepository(session)
    await invoices.create_if_absent(
        manuscript.id, amount_pesewas=DEFAULT_APC_PESEWAS, created_at=NOW
    )
    await session.commit()

    first = await invoices.get_for_manuscript(manuscript.id)
    assert first is not None
    assert first.status == "pending"
    assert first.amount_pesewas == DEFAULT_APC_PESEWAS
    assert first.paystack_reference is None
    assert first.settled_at is None

    # The idempotence half: a second accept decision (or a retried request) must not
    # open a second invoice or replace the first.
    await invoices.create_if_absent(manuscript.id, amount_pesewas=99, created_at=NOW)
    await session.commit()
    second = await invoices.get_for_manuscript(manuscript.id)
    assert second is not None
    assert second.id == first.id
    assert second.amount_pesewas == DEFAULT_APC_PESEWAS


async def test_reference_then_paid_round_trip(session: AsyncSession) -> None:
    manuscript = await _seed_manuscript(session, 602)
    invoices = SqlAlchemyApcInvoiceRepository(session)
    await invoices.create_if_absent(
        manuscript.id, amount_pesewas=DEFAULT_APC_PESEWAS, created_at=NOW
    )
    await invoices.set_reference(manuscript.id, "ref-xyz")
    await invoices.mark_paid(manuscript.id, settled_at=NOW)
    await session.commit()

    invoice = await invoices.get_for_manuscript(manuscript.id)
    assert invoice is not None
    assert invoice.status == "paid"
    assert invoice.paystack_reference == "ref-xyz"
    assert invoice.settled_at is not None


async def test_mark_waived_settles_without_a_reference(session: AsyncSession) -> None:
    manuscript = await _seed_manuscript(session, 603)
    invoices = SqlAlchemyApcInvoiceRepository(session)
    await invoices.create_if_absent(
        manuscript.id, amount_pesewas=DEFAULT_APC_PESEWAS, created_at=NOW
    )
    await invoices.mark_waived(manuscript.id, settled_at=NOW)
    await session.commit()

    invoice = await invoices.get_for_manuscript(manuscript.id)
    assert invoice is not None
    assert invoice.status == "waived"
    assert invoice.paystack_reference is None


async def test_a_manuscript_with_no_invoice_reads_as_none(session: AsyncSession) -> None:
    manuscript = await _seed_manuscript(session, 604)
    invoices = SqlAlchemyApcInvoiceRepository(session)
    assert await invoices.get_for_manuscript(manuscript.id) is None
