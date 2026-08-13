"""APC billing: invoice creation on accept, and the pay/verify/waive lifecycle.

Paystack itself never appears: routes see either `None` (mock mode, the default here
because no `PAYSTACK_SECRET_KEY` is set) or a `FakePaymentGateway` planted through the
`get_payment_gateway` override. The real adapter's HTTP translation is proven with
`httpx.MockTransport` in `tests/unit/infrastructure/test_paystack_gateway.py`.
"""

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from tests.unit.api.fakes import FakePaymentGateway, FakeUnitOfWork, new_user_id
from ugjcs.api.app import create_app
from ugjcs.api.deps import get_current_actor
from ugjcs.api.wiring import get_payment_gateway, get_uow
from ugjcs.application.ports import DEFAULT_APC_PESEWAS, ApcInvoiceRecord
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Actor

AUTHOR = new_user_id()
CO_AUTHOR = new_user_id()
EDITOR = new_user_id()
EIC = new_user_id()
REVIEWER = new_user_id()
NOW = datetime(2026, 8, 13, 9, 0, tzinfo=UTC)

AUTHOR_ACTOR = Actor(id=AUTHOR, roles=frozenset({Role.AUTHOR}))
EDITOR_ACTOR = Actor(id=EDITOR, roles=frozenset({Role.EDITOR}))
EIC_ACTOR = Actor(id=EIC, roles=frozenset({Role.EDITOR_IN_CHIEF}))


def accepted_manuscript(sequence: int) -> Manuscript:
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, sequence),
        title="T",
        abstract="A.",
        keywords=(),
        author_ids=(AUTHOR, CO_AUTHOR),
        corresponding_author_id=AUTHOR,
    )
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    manuscript.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    manuscript.record_decision(
        decision=DecisionType.SEND_TO_REVIEW, actor_id=EDITOR, rationale="ok", occurred_at=NOW
    )
    for _ in range(manuscript.minimum_reviews):
        manuscript.record_review(reviewer_id=REVIEWER, occurred_at=NOW)
    return manuscript


def pending_invoice(manuscript: Manuscript) -> ApcInvoiceRecord:
    return ApcInvoiceRecord(
        id=uuid4(),
        manuscript_id=manuscript.id,
        amount_pesewas=DEFAULT_APC_PESEWAS,
        status="pending",
        paystack_reference=None,
        created_at=NOW,
        settled_at=None,
    )


def make_client(
    actor: Actor, uow: FakeUnitOfWork, gateway: FakePaymentGateway | None = None
) -> TestClient:
    app = create_app()

    async def _uow() -> AsyncIterator[FakeUnitOfWork]:
        yield uow

    app.dependency_overrides[get_uow] = _uow
    app.dependency_overrides[get_current_actor] = lambda: actor
    app.dependency_overrides[get_payment_gateway] = lambda: gateway
    return TestClient(app)


def uow_with(manuscript: Manuscript, invoice: ApcInvoiceRecord | None = None) -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    uow.manuscripts.store[manuscript.id] = manuscript
    if invoice is not None:
        uow.invoices.invoices[manuscript.id] = invoice
    return uow


# --- invoice creation on the decision path ------------------------------------------


def test_an_accept_decision_opens_a_pending_invoice_at_the_default_tariff() -> None:
    manuscript = accepted_manuscript(301)
    uow = uow_with(manuscript)
    client = make_client(EDITOR_ACTOR, uow)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "accept", "rationale": "Sound work."},
    )
    assert response.status_code == 200
    invoice = uow.invoices.invoices[manuscript.id]
    assert invoice.status == "pending"
    assert invoice.amount_pesewas == DEFAULT_APC_PESEWAS


def test_a_non_accept_decision_opens_no_invoice() -> None:
    manuscript = accepted_manuscript(302)
    uow = uow_with(manuscript)
    client = make_client(EDITOR_ACTOR, uow)
    response = client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "reject", "rationale": "Not sound."},
    )
    assert response.status_code == 200
    assert uow.invoices.invoices == {}


def test_a_repeated_accept_path_never_double_bills() -> None:
    """`create_if_absent` semantics, exercised through the fake the way the route uses
    it: an invoice that already exists (whatever its status) is left untouched."""
    manuscript = accepted_manuscript(303)
    existing = pending_invoice(manuscript)
    uow = uow_with(manuscript, existing)
    client = make_client(EDITOR_ACTOR, uow)
    client.post(
        f"/api/v1/editorial/{manuscript.tracking_code.value}/decision",
        json={"decision": "accept", "rationale": "Sound work."},
    )
    assert uow.invoices.invoices[manuscript.id].id == existing.id


# --- reading the invoice -------------------------------------------------------------


def test_the_corresponding_author_can_read_their_invoice() -> None:
    manuscript = accepted_manuscript(304)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(AUTHOR_ACTOR, uow)
    response = client.get(f"/api/v1/billing/{manuscript.tracking_code.value}")
    assert response.status_code == 200
    body = response.json()
    assert body["tracking_code"] == manuscript.tracking_code.value
    assert body["amount_pesewas"] == DEFAULT_APC_PESEWAS
    assert body["status"] == "pending"
    assert body["paystack_reference"] is None


def test_an_editor_can_read_any_invoice() -> None:
    manuscript = accepted_manuscript(305)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(EDITOR_ACTOR, uow)
    assert client.get(f"/api/v1/billing/{manuscript.tracking_code.value}").status_code == 200


def test_a_co_author_cannot_read_the_invoice() -> None:
    """The billing relationship is the *corresponding* author's alone; a co-author can
    see the manuscript but has no business with the invoice."""
    manuscript = accepted_manuscript(306)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(Actor(id=CO_AUTHOR, roles=frozenset({Role.AUTHOR})), uow)
    assert client.get(f"/api/v1/billing/{manuscript.tracking_code.value}").status_code == 403


def test_a_manuscript_without_an_invoice_reads_as_404() -> None:
    manuscript = accepted_manuscript(307)
    uow = uow_with(manuscript)
    client = make_client(AUTHOR_ACTOR, uow)
    assert client.get(f"/api/v1/billing/{manuscript.tracking_code.value}").status_code == 404


def test_an_unknown_tracking_code_reads_as_404() -> None:
    client = make_client(AUTHOR_ACTOR, FakeUnitOfWork())
    assert client.get("/api/v1/billing/SDJ-2026-9999").status_code == 404


# --- initialize ----------------------------------------------------------------------


def test_mock_mode_initialize_settles_the_invoice_and_says_so() -> None:
    """No Paystack key configured (gateway `None`): the demo settles on the spot and
    the response admits it with `"mock": true`."""
    manuscript = accepted_manuscript(308)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(AUTHOR_ACTOR, uow, gateway=None)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/initialize")
    assert response.status_code == 200
    assert response.json()["mock"] is True
    assert response.json()["status"] == "paid"
    assert uow.invoices.invoices[manuscript.id].status == "paid"
    assert uow.invoices.invoices[manuscript.id].settled_at is not None


def test_real_mode_initialize_returns_the_checkout_url_and_stores_the_reference() -> None:
    manuscript = accepted_manuscript(309)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    # Real mode reads the payer's email off their account, so the corresponding author
    # needs a genuine domain `Account` in the repository (a `FakeAccount`'s email is a
    # bare string; the route dereferences `EmailAddress.value`).
    payer = Account(
        id=AUTHOR,
        email=EmailAddress("author@sdj.test"),
        password_hash="argon2-hash",
        full_name="Ama Mensah",
        affiliation="University of Ghana",
        is_verified=True,
    )
    uow.accounts.accounts[AUTHOR] = payer  # type: ignore[assignment]
    gateway = FakePaymentGateway()
    client = make_client(AUTHOR_ACTOR, uow, gateway=gateway)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/initialize")
    assert response.status_code == 200
    body = response.json()
    assert body["mock"] is False
    assert body["status"] == "pending"
    invoice = uow.invoices.invoices[manuscript.id]
    assert invoice.status == "pending"  # nothing settles until verification
    assert invoice.paystack_reference is not None
    expected_url = f"https://checkout.paystack.test/{invoice.paystack_reference}"
    assert body["authorization_url"] == expected_url
    [(email, amount, reference)] = gateway.initialized
    assert email == "author@sdj.test"
    assert amount == DEFAULT_APC_PESEWAS
    assert reference == invoice.paystack_reference


def test_only_the_corresponding_author_may_initialize() -> None:
    manuscript = accepted_manuscript(310)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    for actor in (EDITOR_ACTOR, EIC_ACTOR, Actor(id=CO_AUTHOR, roles=frozenset({Role.AUTHOR}))):
        client = make_client(actor, uow)
        response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/initialize")
        assert response.status_code == 403


def test_initializing_a_settled_invoice_is_a_conflict() -> None:
    manuscript = accepted_manuscript(311)
    invoice = replace(pending_invoice(manuscript), status="paid", settled_at=NOW)
    uow = uow_with(manuscript, invoice)
    client = make_client(AUTHOR_ACTOR, uow)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/initialize")
    assert response.status_code == 409


# --- verify --------------------------------------------------------------------------


def test_verify_marks_paid_when_the_gateway_confirms() -> None:
    manuscript = accepted_manuscript(312)
    invoice = replace(pending_invoice(manuscript), paystack_reference="ref-abc")
    uow = uow_with(manuscript, invoice)
    gateway = FakePaymentGateway(verify_result=True)
    client = make_client(AUTHOR_ACTOR, uow, gateway=gateway)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/verify")
    assert response.status_code == 200
    assert response.json() == {"status": "paid"}
    assert uow.invoices.invoices[manuscript.id].status == "paid"
    assert gateway.verified_references == ["ref-abc"]


def test_verify_leaves_the_invoice_pending_when_the_gateway_does_not_confirm() -> None:
    manuscript = accepted_manuscript(313)
    invoice = replace(pending_invoice(manuscript), paystack_reference="ref-abc")
    uow = uow_with(manuscript, invoice)
    client = make_client(AUTHOR_ACTOR, uow, gateway=FakePaymentGateway(verify_result=False))
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/verify")
    assert response.status_code == 200
    assert response.json() == {"status": "pending"}
    assert uow.invoices.invoices[manuscript.id].status == "pending"


def test_verify_before_initialize_is_a_conflict_in_real_mode() -> None:
    manuscript = accepted_manuscript(314)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(AUTHOR_ACTOR, uow, gateway=FakePaymentGateway())
    assert (
        client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/verify").status_code == 409
    )


def test_verify_is_idempotent_once_paid() -> None:
    manuscript = accepted_manuscript(315)
    invoice = replace(pending_invoice(manuscript), status="paid", settled_at=NOW)
    uow = uow_with(manuscript, invoice)
    gateway = FakePaymentGateway()
    client = make_client(AUTHOR_ACTOR, uow, gateway=gateway)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/verify")
    assert response.status_code == 200
    assert response.json() == {"status": "paid"}
    assert gateway.verified_references == []  # no needless round trip to Paystack


def test_only_the_corresponding_author_may_verify() -> None:
    manuscript = accepted_manuscript(316)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(EDITOR_ACTOR, uow)
    assert (
        client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/verify").status_code == 403
    )


# --- waive ---------------------------------------------------------------------------


def test_the_editor_in_chief_can_waive_an_invoice() -> None:
    manuscript = accepted_manuscript(317)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(EIC_ACTOR, uow)
    response = client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/waive")
    assert response.status_code == 200
    assert response.json()["status"] == "waived"
    assert uow.invoices.invoices[manuscript.id].status == "waived"


def test_a_plain_editor_cannot_waive() -> None:
    manuscript = accepted_manuscript(318)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(EDITOR_ACTOR, uow)
    assert client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/waive").status_code == 403


def test_the_author_cannot_waive_their_own_invoice() -> None:
    manuscript = accepted_manuscript(319)
    uow = uow_with(manuscript, pending_invoice(manuscript))
    client = make_client(AUTHOR_ACTOR, uow)
    assert client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/waive").status_code == 403


def test_waiving_a_paid_invoice_is_a_conflict() -> None:
    manuscript = accepted_manuscript(320)
    invoice = replace(pending_invoice(manuscript), status="paid", settled_at=NOW)
    uow = uow_with(manuscript, invoice)
    client = make_client(EIC_ACTOR, uow)
    assert client.post(f"/api/v1/billing/{manuscript.tracking_code.value}/waive").status_code == 409


def test_every_billing_route_requires_authentication() -> None:
    """No override for `get_current_actor`: a request with no bearer token must be 401
    on every billing route — the auth-guard half of this feature's contract."""
    app = create_app()
    client = TestClient(app)
    assert client.get("/api/v1/billing/SDJ-2026-0001").status_code == 401
    assert client.post("/api/v1/billing/SDJ-2026-0001/initialize").status_code == 401
    assert client.post("/api/v1/billing/SDJ-2026-0001/verify").status_code == 401
    assert client.post("/api/v1/billing/SDJ-2026-0001/waive").status_code == 401
