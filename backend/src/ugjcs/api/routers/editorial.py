"""Screening, decisions, and reviewer assignment — the editor's desk."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status

from ugjcs.api.deps import require as require_action
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.schemas import (
    AssignReviewerRequest,
    ManuscriptOut,
    RecordDecisionRequest,
    ScheduleManuscriptRequest,
)
from ugjcs.api.wiring import UowDep
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import UserId, mint_issue_id
from ugjcs.domain.policies import Action, Actor

router = APIRouter()

# Route-specific aliases, built the same way as `wiring.UowDep`/`deps.ActorDep`: ruff's
# B008 forbids `Depends(require(...))` as a bare default, so each role gate this router
# needs is a module-level `Annotated` alias instead.
ScreenDep = Annotated[Actor, Depends(require_action(Action.SCREEN))]
DecideDep = Annotated[Actor, Depends(require_action(Action.DECIDE))]
AssignReviewerDep = Annotated[Actor, Depends(require_action(Action.ASSIGN_REVIEWER))]
# `Action.PUBLISH` is granted to `Role.EDITOR_IN_CHIEF` alone (`domain/policies.py`), and
# it gates both routes below: scheduling and publishing are the same "the Editor-in-Chief
# commits this manuscript to an issue" authority split into two steps, not two separate
# permissions — there is no `Action.SCHEDULE` in the domain vocabulary to gate with instead.
PublishDep = Annotated[Actor, Depends(require_action(Action.PUBLISH))]


@router.get("/queue", response_model=list[ManuscriptOut])
async def screening_queue(actor: ScreenDep, uow: UowDep) -> list[ManuscriptOut]:
    manuscripts = await uow.manuscripts.list_by_status(S.SUBMITTED)
    return [ManuscriptOut.from_domain(m) for m in manuscripts]


@router.post("/{tracking_code}/screen", response_model=ManuscriptOut)
async def screen(tracking_code: str, actor: ScreenDep, uow: UowDep) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.begin_screening(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/decision", response_model=ManuscriptOut)
async def record_decision(
    tracking_code: str,
    body: RecordDecisionRequest,
    actor: DecideDep,
    uow: UowDep,
) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.record_decision(
        decision=body.decision,
        actor_id=UserId(actor.id),
        rationale=body.rationale,
        occurred_at=datetime.now(UTC),
    )
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/reviewers", status_code=status.HTTP_204_NO_CONTENT)
async def assign_reviewer(
    tracking_code: str,
    body: AssignReviewerRequest,
    actor: AssignReviewerDep,
    uow: UowDep,
) -> None:
    manuscript = await _get_or_404(uow, tracking_code)
    await uow.assignments.assign(
        manuscript.id, UserId(body.reviewer_id), occurred_at=datetime.now(UTC)
    )
    await uow.commit()


@router.post("/{tracking_code}/schedule", response_model=ManuscriptOut)
async def schedule(
    tracking_code: str,
    body: ScheduleManuscriptRequest,
    actor: PublishDep,
    uow: UowDep,
) -> ManuscriptOut:
    """`IssueId` is derived deterministically from `(volume, number)` — see
    `ugjcs.domain.ids.mint_issue_id` for why: issues are not a persisted entity, so this
    is the identifier scheduling has to work with instead of a lookup.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.schedule(
        issue_id=mint_issue_id(body.volume, body.number),
        actor_id=UserId(actor.id),
        occurred_at=datetime.now(UTC),
    )
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)


@router.post("/{tracking_code}/publish", response_model=ManuscriptOut)
async def publish(tracking_code: str, actor: PublishDep, uow: UowDep) -> ManuscriptOut:
    manuscript = await _get_or_404(uow, tracking_code)
    manuscript.publish(actor_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.commit()
    return ManuscriptOut.from_domain(manuscript)
