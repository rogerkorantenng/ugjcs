"""A reviewer's queue and their submissions — blinded, structurally, every time.

`BlindedManuscriptOut.from_domain` takes a `BlindedManuscript`, never a `Manuscript`. A
handler in this file that called `ManuscriptOut.from_domain` on a manuscript instead
would be a type error the moment mypy strict looks at the `response_model`, not a review
comment — that is what "structural" means here, and it is the same guarantee
`ugjcs.domain.blinding` documents for the type itself.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ugjcs.api.deps import require as require_action
from ugjcs.api.routers.manuscripts import _get_or_404, _presigned
from ugjcs.api.schemas import BlindedManuscriptOut, DocumentUrlOut, SubmitReviewRequest
from ugjcs.api.wiring import DocumentStoreDep, UowDep
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.blinding import blind
from ugjcs.domain.ids import ManuscriptId, UserId
from ugjcs.domain.policies import Action, Actor

router = APIRouter()

# `Action.REVIEW` is the single role gate this router needs (see `deps.require`'s note on
# `VIEW`/`RESUBMIT`/`WITHDRAW` being the only actions that also check ownership); built as
# a module-level `Annotated` alias for the same ruff B008 reason as `wiring.UowDep`.
ReviewDep = Annotated[Actor, Depends(require_action(Action.REVIEW))]


@router.get("/mine", response_model=list[BlindedManuscriptOut])
async def my_assignments(actor: ReviewDep, uow: UowDep) -> list[BlindedManuscriptOut]:
    records = await uow.assignments.list_for_reviewer(UserId(actor.id))
    out: list[BlindedManuscriptOut] = []
    for record in records:
        manuscript = await uow.manuscripts.get(record.manuscript_id)
        if manuscript is not None:
            out.append(BlindedManuscriptOut.from_domain(blind(manuscript)))
    return out


@router.post("/{tracking_code}/submit", status_code=status.HTTP_204_NO_CONTENT)
async def submit_review(
    tracking_code: str,
    body: SubmitReviewRequest,
    actor: ReviewDep,
    uow: UowDep,
) -> None:
    manuscript = await _get_or_404(uow, tracking_code)
    await _assigned_or_403(uow, manuscript.id, UserId(actor.id))
    manuscript.record_review(reviewer_id=UserId(actor.id), occurred_at=datetime.now(UTC))
    await uow.manuscripts.save(manuscript)
    await uow.assignments.mark_submitted(
        manuscript.id,
        UserId(actor.id),
        recommendation=body.recommendation,
        comments=body.comments,
        occurred_at=datetime.now(UTC),
    )
    await uow.commit()


@router.get("/{tracking_code}/document", response_model=DocumentUrlOut)
async def get_document(
    tracking_code: str,
    actor: ReviewDep,
    uow: UowDep,
    documents: DocumentStoreDep,
) -> DocumentUrlOut:
    """The reviewer's counterpart to `manuscripts.get_document`, deliberately unable to
    reuse it: this route has no `variant` parameter at all, because a reviewer must never
    even have the *option* of requesting `manuscript.original_document_key` — the
    double-blind guarantee is enforced by this route's shape, not by a check inside it.
    """
    manuscript = await _get_or_404(uow, tracking_code)
    await _assigned_or_403(uow, manuscript.id, UserId(actor.id))
    if manuscript.anonymised_document_key is None:
        raise HTTPException(status_code=404, detail="no document has been attached")
    return await _presigned(documents, manuscript.anonymised_document_key)


async def _assigned_or_403(
    uow: UnitOfWork, manuscript_id: ManuscriptId, reviewer_id: UserId
) -> None:
    assigned = {
        record.manuscript_id for record in await uow.assignments.list_for_reviewer(reviewer_id)
    }
    if manuscript_id not in assigned:
        raise HTTPException(status_code=403, detail="you were not assigned this manuscript")
