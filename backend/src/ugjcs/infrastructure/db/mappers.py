"""Translation between domain aggregates and storage rows.

Kept apart from `models.py` because the two change for different reasons: models change
with the schema, mappers with the domain.
"""

from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import ChainedEvent
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.models import (
    EditorialEventRow,
    ManuscriptAuthorRow,
    ManuscriptRow,
)


def to_row(manuscript: Manuscript) -> ManuscriptRow:
    """Project an aggregate onto a storage row, authors included in order."""
    return ManuscriptRow(
        id=manuscript.id,
        tracking_code=manuscript.tracking_code.value,
        title=manuscript.title,
        abstract=manuscript.abstract,
        keywords=list(manuscript.keywords),
        corresponding_author_id=manuscript.corresponding_author_id,
        status=manuscript.status.value,
        version=manuscript.version,
        minimum_reviews=manuscript.minimum_reviews,
        submitted_reviews=manuscript.submitted_reviews,
        issue_id=manuscript.issue_id,
        authors=[
            ManuscriptAuthorRow(manuscript_id=manuscript.id, author_id=author_id, position=position)
            for position, author_id in enumerate(manuscript.author_ids)
        ],
    )


def to_domain(row: ManuscriptRow, *, last_sequence: int) -> Manuscript:
    """Rebuild an aggregate, restoring the monotonic event sequence counter.

    `last_sequence` must be the highest sequence already persisted for this manuscript.
    Passing 0 means no events exist yet. Getting this wrong silently reissues a sequence
    number that is already in the chain, and `hashchain.append` will reject the next event.
    """
    manuscript = Manuscript(
        id=ManuscriptId(row.id),
        tracking_code=TrackingCode.parse(row.tracking_code),
        title=row.title,
        abstract=row.abstract,
        keywords=tuple(row.keywords),
        author_ids=tuple(UserId(author.author_id) for author in row.authors),
        corresponding_author_id=UserId(row.corresponding_author_id),
        status=S(row.status),
        version=row.version,
        minimum_reviews=row.minimum_reviews,
        submitted_reviews=row.submitted_reviews,
        issue_id=IssueId(row.issue_id) if row.issue_id is not None else None,
    )
    manuscript._sequence = last_sequence
    return manuscript


def event_to_row(chained: ChainedEvent, manuscript_id: ManuscriptId) -> EditorialEventRow:
    """Store a linked event, hashes and all."""
    return EditorialEventRow(
        manuscript_id=manuscript_id,
        sequence=chained.event.sequence,
        event_type=chained.event.event_type.value,
        payload=dict(chained.event.payload),
        actor_id=chained.event.actor_id,
        occurred_at=chained.event.occurred_at,
        previous_hash=chained.previous_hash,
        event_hash=chained.event_hash,
    )


def row_to_chained(row: EditorialEventRow) -> ChainedEvent:
    """Rebuild a linked event exactly as it was hashed."""
    payload: dict[str, PayloadValue] = dict(row.payload)  # type: ignore[arg-type]
    return ChainedEvent(
        event=EditorialEvent(
            manuscript_id=ManuscriptId(row.manuscript_id),
            sequence=row.sequence,
            event_type=EventType(row.event_type),
            payload=payload,
            actor_id=UserId(row.actor_id) if row.actor_id is not None else None,
            occurred_at=row.occurred_at,
        ),
        previous_hash=row.previous_hash,
        event_hash=row.event_hash,
    )
