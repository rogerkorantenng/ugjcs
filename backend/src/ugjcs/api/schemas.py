"""Wire shapes. The domain must never import pydantic — these live here, not there."""

from uuid import UUID

from pydantic import BaseModel

from ugjcs.application.ports import AccountRepository
from ugjcs.domain.enums import DecisionType
from ugjcs.domain.manuscript import Manuscript


class ManuscriptOut(BaseModel):
    """The one shape every manuscript route returns; no separate summary/detail variant.

    Deliberately absent, per `docs/05-api-contract.md` §7: `id` (`tracking_code` is the
    only identifier on the wire), any timestamp, and any event/audit trail.
    """

    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_ids: tuple[UUID, ...]
    corresponding_author_id: UUID
    status: str
    version: int
    minimum_reviews: int
    submitted_reviews: int

    @classmethod
    def from_domain(cls, manuscript: Manuscript) -> "ManuscriptOut":
        return cls(
            tracking_code=manuscript.tracking_code.value,
            title=manuscript.title,
            abstract=manuscript.abstract,
            keywords=manuscript.keywords,
            author_ids=tuple(UUID(str(a)) for a in manuscript.author_ids),
            corresponding_author_id=UUID(str(manuscript.corresponding_author_id)),
            status=manuscript.status.value,
            version=manuscript.version,
            minimum_reviews=manuscript.minimum_reviews,
            submitted_reviews=manuscript.submitted_reviews,
        )


class SubmitManuscriptRequest(BaseModel):
    title: str
    abstract: str
    keywords: tuple[str, ...]
    co_author_ids: tuple[UUID, ...] = ()


class RecordDecisionRequest(BaseModel):
    decision: DecisionType
    rationale: str


class AssignReviewerRequest(BaseModel):
    reviewer_id: UUID


class ArchivePaperOut(BaseModel):
    """The public shape: a byline a human (or Google Scholar) can read, never a UUID.

    Deliberately not `ManuscriptOut` (author-facing, carries raw `author_ids`/
    `corresponding_author_id` UUIDs): a public, anonymous-caller endpoint has no reason
    to leak internal account identifiers, and a UUID is useless as a citation byline.
    """

    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    author_names: list[str]
    status: str
    version: int

    @classmethod
    async def from_domain(
        cls, manuscript: Manuscript, accounts: AccountRepository
    ) -> "ArchivePaperOut":
        names: list[str] = []
        for author_id in manuscript.author_ids:
            account = await accounts.get(author_id)
            names.append(account.full_name if account is not None else "Unknown author")
        return cls(
            tracking_code=manuscript.tracking_code.value,
            title=manuscript.title,
            abstract=manuscript.abstract,
            keywords=manuscript.keywords,
            author_names=names,
            status=manuscript.status.value,
            version=manuscript.version,
        )
