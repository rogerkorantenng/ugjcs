"""An author's own view of their submissions."""

from datetime import UTC, datetime
from random import randint
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from ugjcs.api.deps import ActorDep, require
from ugjcs.api.schemas import ManuscriptOut, SubmitManuscriptRequest
from ugjcs.api.wiring import UowDep
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.policies import Action, Actor, authorize

router = APIRouter()

# A route-specific alias, built the same way as `wiring.UowDep`/`deps.ActorDep`: the
# `require(Action.SUBMIT)` call must not appear as a bare `Depends(...)` default (ruff
# B008), and this is the only route in this file that needs role enforcement before the
# handler runs — `retrieve`/`withdraw` authorise against the loaded manuscript instead.
SubmitDep = Annotated[Actor, Depends(require(Action.SUBMIT))]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ManuscriptOut)
async def submit_manuscript(
    body: SubmitManuscriptRequest, actor: SubmitDep, uow: UowDep
) -> ManuscriptOut:
    author_ids = (UserId(actor.id), *(UserId(uid) for uid in body.co_author_ids))
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=_mint_tracking_code(),
        title=body.title,
        abstract=body.abstract,
        keywords=body.keywords,
        author_ids=author_ids,
        corresponding_author_id=UserId(actor.id),
    )
    manuscript.submit(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
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
