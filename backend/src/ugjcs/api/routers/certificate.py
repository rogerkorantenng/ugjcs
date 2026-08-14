"""Editorial decision certificates — a PDF record of an accept/reject decision.

Gated by `Action.DECIDE` (granted to `EDITOR` and `EDITOR_IN_CHIEF`, exactly the roles
asked for), the same grant `record_decision` and `list_reviews` carry: the certificate
prints review content, so it must be reachable by precisely the actors who can already
read reviews, and nobody else. Reviews appear by ordinal ("Reviewer 1"), never by name
or identifier, and only `comments_to_author` is printed — the confidential comments to
the editor are never passed to the PDF builder at all.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ugjcs.api.deps import require
from ugjcs.api.routers.manuscripts import _get_or_404
from ugjcs.api.wiring import UowDep
from ugjcs.domain.enums import DecisionType, EventType
from ugjcs.domain.hashchain import GENESIS_HASH, ChainedEvent
from ugjcs.domain.policies import Action, Actor
from ugjcs.infrastructure.storage.certificate_pdf import ReviewSummary, build_certificate_pdf

router = APIRouter()

# See `wiring.UowDep` for why this is a module-level alias rather than a bare
# `Depends(require(...))` default (ruff B008).
CertificateDep = Annotated[Actor, Depends(require(Action.DECIDE))]

_FINAL_DECISIONS = frozenset({DecisionType.ACCEPT.value, DecisionType.REJECT.value})


def _final_decision(chain: list[ChainedEvent]) -> tuple[str, str] | None:
    """The latest recorded accept/reject `(decision, rationale)`, from the event chain.

    The chain is where the rationale lives — the aggregate materialises only status —
    and reading it here also keeps the certificate consistent with the provenance
    endpoint: both describe the same audit history.
    """
    for link in reversed(chain):
        event = link.event
        if event.event_type is not EventType.DECISION_RECORDED:
            continue
        decision = event.payload.get("decision")
        if isinstance(decision, str) and decision in _FINAL_DECISIONS:
            rationale = event.payload.get("rationale")
            return decision, rationale if isinstance(rationale, str) else ""
    return None


@router.get("/{tracking_code}")
async def decision_certificate(tracking_code: str, actor: CertificateDep, uow: UowDep) -> Response:
    """`application/pdf`: masthead, tracking code, title, the decision with its
    rationale, each submitted review by ordinal, and the audit-chain head hash as a
    provenance line. 409 until an accept or reject decision has been recorded."""
    manuscript = await _get_or_404(uow, tracking_code)
    chain = await uow.manuscripts.chain_for(manuscript.id)
    decision = _final_decision(chain)
    if decision is None:
        raise HTTPException(
            status_code=409, detail="no accept or reject decision has been recorded"
        )
    records = await uow.assignments.list_for_manuscript(manuscript.id)
    reviews = [
        ReviewSummary(
            recommendation=record.recommendation,
            originality_score=record.originality_score,
            rigour_score=record.rigour_score,
            clarity_score=record.clarity_score,
            significance_score=record.significance_score,
            comments_to_author=record.comments_to_author,
        )
        for record in records
        if record.status == "submitted"
    ]
    pdf = build_certificate_pdf(
        tracking_code=manuscript.tracking_code.value,
        title=manuscript.title,
        decision=decision[0],
        rationale=decision[1],
        reviews=reviews,
        head_hash=chain[-1].event_hash if chain else GENESIS_HASH,
    )
    return Response(content=pdf, media_type="application/pdf")
