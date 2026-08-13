"""APC billing: the corresponding author settles (or the Editor-in-Chief waives) the
article processing charge an accept decision opened.

Two modes, decided by configuration alone (`Settings.paystack_secret_key`):

- **Real mode** — initialize opens a Paystack checkout and returns its
  `authorization_url`; verify asks Paystack whether the referenced charge succeeded.
- **Mock mode** (blank key, the demonstration default) — initialize settles the invoice
  immediately and answers `{"mock": true, ...}`, so the flow completes end-to-end
  without a card or a key. The `mock` flag is on the wire deliberately: a demo must
  say it is one.

The Paystack secret key never enters this module: it lives inside the adapter the
wiring constructs, and no billing response, log line or error detail can carry it.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from ugjcs.api.deps import ActorDep
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.schemas_wave2 import ApcInvoiceOut, BillingInitializeOut, BillingVerifyOut
from ugjcs.api.wiring import PaymentGatewayDep, UowDep
from ugjcs.application.ports import ApcInvoiceRecord, UnitOfWork
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor
from ugjcs.infrastructure.payments.paystack import PaystackError

router = APIRouter()

# Editors, the Editor-in-Chief and administrators may *see* an invoice (chasing payment
# is desk work); only the corresponding author may pay one, and only the Editor-in-Chief
# may waive one — each route below states its own gate.
_EDITORIAL_ROLES = frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF, Role.ADMINISTRATOR})


@router.get("/{tracking_code}", response_model=ApcInvoiceOut)
async def get_invoice(tracking_code: str, actor: ActorDep, uow: UowDep) -> ApcInvoiceOut:
    manuscript, invoice = await _invoice_or_404(uow, tracking_code)
    if actor.id != manuscript.corresponding_author_id and not (actor.roles & _EDITORIAL_ROLES):
        # 403, not 404: the tracking code's existence is not a secret (co-authors can
        # see the manuscript), only the billing relationship is restricted.
        raise HTTPException(status_code=403, detail="not this invoice's payer or an editor")
    return ApcInvoiceOut.from_record(invoice, tracking_code=manuscript.tracking_code.value)


@router.post("/{tracking_code}/initialize", response_model=BillingInitializeOut)
async def initialize_payment(
    tracking_code: str, actor: ActorDep, uow: UowDep, gateway: PaymentGatewayDep
) -> BillingInitializeOut:
    """Open a checkout for the invoice — or, in mock mode, settle it on the spot."""
    manuscript, invoice = await _invoice_or_404(uow, tracking_code)
    _require_corresponding_author(actor, manuscript)
    if invoice.status != "pending":
        raise HTTPException(status_code=409, detail=f"invoice is already {invoice.status}")

    if gateway is None:
        # Mock mode: no Paystack key is configured, so the demo settles immediately.
        await uow.invoices.mark_paid(manuscript.id, settled_at=datetime.now(UTC))
        await uow.commit()
        return BillingInitializeOut(mock=True, status="paid")

    payer = await uow.accounts.get(UserId(actor.id))
    if payer is None:  # pragma: no cover - an authenticated actor always has an account
        raise HTTPException(status_code=404, detail="payer account not found")
    # Our reference, minted and persisted before Paystack ever sees it, so a crash
    # mid-flight leaves a verifiable trail rather than an orphaned charge.
    reference = uuid4().hex
    try:
        url = await gateway.initialize_transaction(
            email=payer.email.value,
            amount_minor_units=invoice.amount_pesewas,
            reference=reference,
        )
    except PaystackError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    await uow.invoices.set_reference(manuscript.id, reference)
    await uow.commit()
    return BillingInitializeOut(mock=False, status="pending", authorization_url=url)


@router.post("/{tracking_code}/verify", response_model=BillingVerifyOut)
async def verify_payment(
    tracking_code: str, actor: ActorDep, uow: UowDep, gateway: PaymentGatewayDep
) -> BillingVerifyOut:
    """Ask Paystack whether the initialized charge went through, and record it if so.

    Idempotent from the caller's side: verifying an already-paid invoice reports
    `"paid"` again rather than erroring, because the author's browser returning from
    Paystack's redirect may retry freely.
    """
    manuscript, invoice = await _invoice_or_404(uow, tracking_code)
    _require_corresponding_author(actor, manuscript)
    if invoice.status == "paid":
        return BillingVerifyOut(status="paid")
    if invoice.status == "waived":
        raise HTTPException(status_code=409, detail="invoice was waived; nothing to verify")

    if gateway is None:
        # Mock mode: a pending invoice being "verified" settles it, mirroring what
        # initialize already does, so no demo path can strand an invoice unpaid.
        await uow.invoices.mark_paid(manuscript.id, settled_at=datetime.now(UTC))
        await uow.commit()
        return BillingVerifyOut(status="paid")

    if invoice.paystack_reference is None:
        raise HTTPException(status_code=409, detail="payment was never initialized")
    try:
        settled = await gateway.verify_transaction(invoice.paystack_reference)
    except PaystackError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    if not settled:
        return BillingVerifyOut(status=invoice.status)
    await uow.invoices.mark_paid(manuscript.id, settled_at=datetime.now(UTC))
    await uow.commit()
    return BillingVerifyOut(status="paid")


@router.post("/{tracking_code}/waive", response_model=ApcInvoiceOut)
async def waive_invoice(tracking_code: str, actor: ActorDep, uow: UowDep) -> ApcInvoiceOut:
    """Editor-in-Chief only: forgive the charge (fee waivers are journal policy for
    authors who cannot pay). Checked by role directly rather than through
    `require(Action.PUBLISH)` — reusing the publish grant would be a lie about what
    this action is, and the domain vocabulary has no billing action to borrow."""
    manuscript, invoice = await _invoice_or_404(uow, tracking_code)
    if Role.EDITOR_IN_CHIEF not in actor.roles:
        raise HTTPException(status_code=403, detail="only the Editor-in-Chief may waive an APC")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="invoice is already paid; nothing to waive")
    await uow.invoices.mark_waived(manuscript.id, settled_at=datetime.now(UTC))
    await uow.commit()
    updated = await uow.invoices.get_for_manuscript(manuscript.id)
    assert updated is not None  # the row was just updated inside this transaction
    return ApcInvoiceOut.from_record(updated, tracking_code=manuscript.tracking_code.value)


def _require_corresponding_author(actor: Actor, manuscript: Manuscript) -> None:
    """Paying is the corresponding author's alone — not co-authors (they never owe the
    APC personally) and not editors (an editor initializing a checkout would bind the
    author to a Paystack transaction they never opened)."""
    if actor.id != manuscript.corresponding_author_id:
        raise HTTPException(
            status_code=403, detail="only the corresponding author may settle this invoice"
        )


async def _invoice_or_404(
    uow: UnitOfWork, tracking_code: str
) -> tuple[Manuscript, ApcInvoiceRecord]:
    """The manuscript and its invoice, or 404 — a manuscript with no accept decision
    yet has no invoice, and that absence is expressed as not-found, not as an empty
    invoice a client might mistake for "nothing owed"."""
    manuscript = await _get_or_404(uow, tracking_code)
    invoice = await uow.invoices.get_for_manuscript(manuscript.id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="no invoice exists for this manuscript")
    return manuscript, invoice
