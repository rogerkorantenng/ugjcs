"""Wire shapes for the wave-2 features: APC billing, the admin console, and full-text
archive search. A separate module from `schemas.py` by the same file-per-concern split
that put analytics in `schemas_analytics.py` — these change with their features, not
with the core manuscript contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ugjcs.api.schemas import ArchivePaperOut
from ugjcs.application.ports import AccountRepository, ApcInvoiceRecord, PublishedSearchHit
from ugjcs.domain.account import Account
from ugjcs.domain.enums import Role


class ApcInvoiceOut(BaseModel):
    """An article processing charge as its owner (or an editor) sees it.

    Keyed by `tracking_code` on the wire like every other manuscript resource; the
    invoice row's own UUID stays internal. `paystack_reference` is this API's minted
    transaction reference — not a secret, and its owner needs it to reconcile a card
    statement — while the Paystack secret key appears nowhere in any billing shape,
    by construction.
    """

    tracking_code: str
    amount_pesewas: int
    status: str
    paystack_reference: str | None
    created_at: datetime
    settled_at: datetime | None

    @classmethod
    def from_record(cls, record: ApcInvoiceRecord, *, tracking_code: str) -> "ApcInvoiceOut":
        return cls(
            tracking_code=tracking_code,
            amount_pesewas=record.amount_pesewas,
            status=record.status,
            paystack_reference=record.paystack_reference,
            created_at=record.created_at,
            settled_at=record.settled_at,
        )


class BillingInitializeOut(BaseModel):
    """What `POST /billing/{code}/initialize` answers, in both of its modes.

    `mock=True` (no Paystack key configured) means the invoice was settled on the spot
    so the demonstration flow completes without a card; `authorization_url` is then
    absent. Real mode inverts both: `mock=False`, a checkout URL to redirect to, and a
    status still `"pending"` until verification. One model for both, because a caller
    must branch on `mock` explicitly rather than duck-type its way into treating a
    demo settlement as a real payment.
    """

    mock: bool
    status: str
    authorization_url: str | None = None


class BillingVerifyOut(BaseModel):
    """The invoice status after a verification round trip: `"paid"` if Paystack (or
    mock mode) confirmed the charge, else the unchanged current status."""

    status: str


class AdminAccountOut(BaseModel):
    """The admin console's roster row — the one shape that serves email, activation and
    verification state together, which is why it exists only behind
    `Action.MANAGE_USERS` and is built by no other router."""

    id: UUID
    email: str
    full_name: str
    affiliation: str
    roles: list[str]
    reviewer_capacity: int
    is_active: bool
    is_verified: bool

    @classmethod
    def from_domain(cls, account: Account) -> "AdminAccountOut":
        return cls(
            id=UUID(str(account.id)),
            email=account.email.value,
            full_name=account.full_name,
            affiliation=account.affiliation,
            # Sorted for a stable wire order: `Account.roles` is a frozenset, and an
            # admin UI diffing consecutive responses must not see phantom changes.
            roles=sorted(role.value for role in account.roles),
            reviewer_capacity=account.reviewer_capacity,
            is_active=account.is_active,
            is_verified=account.is_verified,
        )


class RoleChangeRequest(BaseModel):
    """Grant (`grant=true`) or revoke (`grant=false`) one role. The administrator role
    itself is refused by the route regardless of this body — see `routers.admin`."""

    role: Role
    grant: bool


class CapacityChangeRequest(BaseModel):
    """1..10 enforced here so an out-of-range capacity is a 422 before any handler runs;
    the ceiling is policy (no reviewer juggles more than ten), the floor keeps a
    "capacity zero" account from masquerading as a soft deactivation."""

    reviewer_capacity: int = Field(ge=1, le=10)


class ActiveChangeRequest(BaseModel):
    is_active: bool


class ArchiveSearchResultOut(ArchivePaperOut):
    """`ArchivePaperOut` plus where a full-text match landed.

    `snippet` is a `ts_headline` fragment (match terms wrapped in `<b>…</b>`) when the
    query matched the paper's extracted body text, and `None` when the match came from
    title/abstract/keywords — see `PublishedSearchHit`. Subclassing keeps this
    structurally "the archive shape, plus one field", so the list endpoint and the
    search endpoint can never drift apart silently.
    """

    snippet: str | None = None

    @classmethod
    async def from_hit(
        cls, hit: PublishedSearchHit, accounts: AccountRepository
    ) -> "ArchiveSearchResultOut":
        base = await ArchivePaperOut.from_domain(hit.manuscript, accounts)
        return cls(**base.model_dump(), snippet=hit.snippet)
