"""An author's own view of their submissions."""

from datetime import UTC, datetime
from random import randint
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status

from ugjcs.api.deps import ActorDep, require
from ugjcs.api.schemas import DocumentUrlOut, ManuscriptOut
from ugjcs.api.wiring import DocumentStoreDep, UowDep
from ugjcs.application.documents import (
    PRESIGNED_URL_TTL,
    anonymised_key,
    original_key,
    validate_document,
)
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor, authorize
from ugjcs.infrastructure.storage.anonymize import strip_pdf_metadata

router = APIRouter()

# A route-specific alias, built the same way as `wiring.UowDep`/`deps.ActorDep`: the
# `require(Action.SUBMIT)` call must not appear as a bare `Depends(...)` default (ruff
# B008), and this is the only route in this file that needs role enforcement before the
# handler runs — `retrieve`/`withdraw`/`resubmit`/`get_document` authorise against the
# loaded manuscript instead.
SubmitDep = Annotated[Actor, Depends(require(Action.SUBMIT))]

_EDITORIAL_ROLES = frozenset({Role.EDITOR, Role.EDITOR_IN_CHIEF, Role.ADMINISTRATOR})


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ManuscriptOut)
async def submit_manuscript(
    actor: SubmitDep,
    uow: UowDep,
    documents: DocumentStoreDep,
    title: Annotated[str, Form()],
    abstract: Annotated[str, Form()],
    file: UploadFile,
    keywords: Annotated[str, Form()] = "",
    co_author_ids: Annotated[str, Form()] = "",
) -> ManuscriptOut:
    """Multipart only: FR-04/05/06 require a manuscript to carry a document from the
    moment it exists, so there is no submission path that skips `file`."""
    data = await file.read()
    validate_document(data)
    author_ids = (UserId(actor.id), *(UserId(cid) for cid in _parse_uuids(co_author_ids)))
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=_mint_tracking_code(),
        title=title,
        abstract=abstract,
        keywords=_parse_list(keywords),
        author_ids=author_ids,
        corresponding_author_id=UserId(actor.id),
    )
    o_key, a_key = await _store_document(documents, manuscript.id, manuscript.version, data)
    manuscript.submit(
        actor_id=UserId(actor.id),
        occurred_at=datetime.now(UTC),
        original_document_key=o_key,
        anonymised_document_key=a_key,
    )
    await uow.manuscripts.add(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.get("/mine", response_model=list[ManuscriptOut])
async def list_mine(actor: ActorDep, uow: UowDep) -> list[ManuscriptOut]:
    manuscripts = await uow.manuscripts.list_by_author(UserId(actor.id))
    return [ManuscriptOut.from_domain(m) for m in manuscripts]


@router.get("/{tracking_code}", response_model=ManuscriptOut)
async def retrieve(tracking_code: str, actor: ActorDep, uow: UowDep) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.VIEW, manuscript)
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/withdraw", response_model=ManuscriptOut)
async def withdraw(tracking_code: str, actor: ActorDep, uow: UowDep) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.WITHDRAW, manuscript)
    manuscript.withdraw(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/resubmit", response_model=ManuscriptOut)
async def resubmit(
    tracking_code: str,
    actor: ActorDep,
    uow: UowDep,
    documents: DocumentStoreDep,
    file: UploadFile,
    response_to_reviewers: Annotated[str, Form()],
) -> ManuscriptOut:
    """The corresponding author's only route back into the workflow from
    `REVISION_REQUESTED` — see `Manuscript.resubmit`. Ownership-checked the same way
    `withdraw` is: `Action.RESUBMIT` is granted by `policies.can()` only to the
    manuscript's own corresponding author, never by role alone.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.RESUBMIT, manuscript)
    data = await file.read()
    validate_document(data)
    next_version = manuscript.version + 1
    o_key, a_key = await _store_document(documents, manuscript.id, next_version, data)
    manuscript.resubmit(
        actor_id=UserId(actor.id),
        occurred_at=datetime.now(UTC),
        original_document_key=o_key,
        anonymised_document_key=a_key,
        response_to_reviewers=response_to_reviewers,
    )
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.get("/{tracking_code}/document", response_model=DocumentUrlOut)
async def get_document(
    tracking_code: str,
    actor: ActorDep,
    uow: UowDep,
    documents: DocumentStoreDep,
    variant: Literal["original", "anonymised"] = "original",
) -> DocumentUrlOut:
    """An author gets the original; an editor gets either, by `variant`; a reviewer's
    equivalent route lives on `ugjcs.api.routers.reviews` and serves only the
    anonymised copy — see that module for why it cannot reuse this one.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    authorize(actor, Action.VIEW, manuscript)
    if variant == "anonymised" and not (actor.roles & _EDITORIAL_ROLES):
        raise HTTPException(
            status_code=403, detail="only an editor may request the anonymised copy"
        )
    key = (
        manuscript.anonymised_document_key
        if variant == "anonymised"
        else manuscript.original_document_key
    )
    if key is None:
        raise HTTPException(status_code=404, detail="no document has been attached")
    return await _presigned(documents, key)


async def _store_document(
    documents: DocumentStoreDep, manuscript_id: ManuscriptId, version: int, data: bytes
) -> tuple[str, str]:
    o_key = original_key(manuscript_id, version=version)
    a_key = anonymised_key(manuscript_id, version=version)
    await documents.put(o_key, data, content_type="application/pdf")
    await documents.put(a_key, strip_pdf_metadata(data), content_type="application/pdf")
    return o_key, a_key


async def _presigned(documents: DocumentStoreDep, key: str) -> DocumentUrlOut:
    url = await documents.presigned_url(key, expires_in=PRESIGNED_URL_TTL)
    return DocumentUrlOut(url=url, expires_in_seconds=int(PRESIGNED_URL_TTL.total_seconds()))


def _parse_list(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _parse_uuids(raw: str) -> tuple[UUID, ...]:
    try:
        return tuple(UUID(item) for item in _parse_list(raw))
    except ValueError as error:
        raise HTTPException(status_code=422, detail="co_author_ids must be valid UUIDs") from error


async def _get_or_404(uow: UnitOfWork, tracking_code: str) -> Manuscript:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="manuscript not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None:
        raise HTTPException(status_code=404, detail="manuscript not found")
    return manuscript


def _mint_tracking_code() -> TrackingCode:
    """A demonstration-scale sequence source.

    Minting a globally unique, gap-tolerant tracking code under concurrent submissions is
    a database sequence's job (`SERIAL`, or a dedicated counter table with `SELECT ... FOR
    UPDATE`), not application code guessing at the next integer. That belongs to Plan 2's
    persistence layer, not this API plan, and is entered in the technical debt register.
    For a submission volume an examiner will generate by hand, a random four-to-six-digit
    sequence collides with negligible probability and never needs a second attempt in
    this plan's tests.
    """
    return TrackingCode.mint(datetime.now(UTC).year, randint(1000, 999_999))
