"""Wire shapes. The domain must never import pydantic — these live here, not there."""

from dataclasses import asdict
from uuid import UUID

from pydantic import BaseModel

from ugjcs.application.ports import AccountRepository
from ugjcs.domain.blinding import BlindedManuscript
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
    has_document: bool
    """Whether a document has been attached, without exposing its storage key: the key
    is an implementation detail reached only through `GET .../document`'s pre-signed URL,
    never echoed on the manuscript resource itself."""

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
            has_document=manuscript.original_document_key is not None,
        )


class RecordDecisionRequest(BaseModel):
    decision: DecisionType
    rationale: str


class AssignReviewerRequest(BaseModel):
    reviewer_id: UUID


class ScheduleManuscriptRequest(BaseModel):
    """Which issue to schedule into. Issues are not a persisted entity (see
    `ugjcs.domain.ids.mint_issue_id`), so the caller names one by volume and number
    rather than by an id it would otherwise have to invent or look up."""

    volume: int
    number: int


class DocumentUrlOut(BaseModel):
    """A short-lived, single-use-in-spirit link — see `DocumentStore.presigned_url`."""

    url: str
    expires_in_seconds: int


class BlindedManuscriptOut(BaseModel):
    """The reviewer-facing shape — built from `BlindedManuscript`, never from `Manuscript`.

    Exactly the six fields `ugjcs.domain.blinding.BlindedManuscript` carries: there is no
    `author_ids` or `corresponding_author_id` field on this model at all, matching the
    domain type's structural guarantee rather than merely filtering one that has them.
    """

    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    version: int
    status: str

    @classmethod
    def from_domain(cls, blinded: BlindedManuscript) -> "BlindedManuscriptOut":
        return cls(**asdict(blinded))


class SubmitReviewRequest(BaseModel):
    recommendation: str
    comments: str


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
