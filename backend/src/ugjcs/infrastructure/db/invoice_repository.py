"""PostgreSQL implementation of the APC invoice repository port.

Status transitions here are dumb single-column updates on purpose: whether a payment
*may* be marked paid (right caller, right invoice state) is decided in the billing
router before any of these methods run, and the schema's CHECK constraint keeps the
vocabulary closed. This adapter only records outcomes.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import ApcInvoiceRecord
from ugjcs.domain.ids import ManuscriptId
from ugjcs.infrastructure.db.mappers import invoice_row_to_record
from ugjcs.infrastructure.db.models import ApcInvoiceRow


class SqlAlchemyApcInvoiceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_if_absent(
        self, manuscript_id: ManuscriptId, *, amount_pesewas: int, created_at: datetime
    ) -> None:
        # Precheck rather than INSERT ... ON CONFLICT: the decision route calls this
        # inside a unit of work that must stay ORM-visible (a raw upsert would bypass
        # the identity map), and at this journal's concurrency a lost race falls back
        # to the UNIQUE constraint anyway — loudly, which is the correct failure.
        if await self._get_row(manuscript_id) is not None:
            return
        self._session.add(
            ApcInvoiceRow(
                id=uuid4(),
                manuscript_id=manuscript_id,
                amount_pesewas=amount_pesewas,
                status="pending",
                paystack_reference=None,
                created_at=created_at,
                settled_at=None,
            )
        )

    async def get_for_manuscript(self, manuscript_id: ManuscriptId) -> ApcInvoiceRecord | None:
        row = await self._get_row(manuscript_id)
        return invoice_row_to_record(row) if row is not None else None

    async def set_reference(self, manuscript_id: ManuscriptId, reference: str) -> None:
        row = await self._require_row(manuscript_id)
        row.paystack_reference = reference

    async def mark_paid(self, manuscript_id: ManuscriptId, *, settled_at: datetime) -> None:
        row = await self._require_row(manuscript_id)
        row.status = "paid"
        row.settled_at = settled_at

    async def mark_waived(self, manuscript_id: ManuscriptId, *, settled_at: datetime) -> None:
        row = await self._require_row(manuscript_id)
        row.status = "waived"
        row.settled_at = settled_at

    async def _get_row(self, manuscript_id: ManuscriptId) -> ApcInvoiceRow | None:
        result = await self._session.execute(
            select(ApcInvoiceRow).where(ApcInvoiceRow.manuscript_id == manuscript_id)
        )
        return result.scalar_one_or_none()

    async def _require_row(self, manuscript_id: ManuscriptId) -> ApcInvoiceRow:
        row = await self._get_row(manuscript_id)
        if row is None:
            raise LookupError(f"manuscript {manuscript_id} has no APC invoice")
        return row
