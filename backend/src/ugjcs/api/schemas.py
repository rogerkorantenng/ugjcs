"""Wire shapes. The domain must never import pydantic — these live here, not there."""

from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ugjcs.application.ports import AccountRepository, ReviewAssignmentRecord
from ugjcs.domain.account import Account
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
    """FR-11's structured review: four 1-5 criterion scores, an overall recommendation,
    comments meant for the author, and comments meant for the editor alone.

    `confidential_comments_to_editor` is the field that must never reach an author —
    see `ReviewOut`'s docstring for where that guarantee is actually enforced.
    """

    recommendation: str
    originality_score: int = Field(ge=1, le=5)
    rigour_score: int = Field(ge=1, le=5)
    clarity_score: int = Field(ge=1, le=5)
    significance_score: int = Field(ge=1, le=5)
    comments_to_author: str
    confidential_comments_to_editor: str


class ReviewOut(BaseModel):
    """A submitted review, confidential comments included — see `list_reviews` in
    `ugjcs.api.routers.editorial` for the one route this model is ever returned from.
    No route reachable by an author or a reviewer builds this model; only the
    `Action.DECIDE`-gated editorial route does."""

    reviewer_id: UUID
    status: str
    recommendation: str | None
    originality_score: int | None
    rigour_score: int | None
    clarity_score: int | None
    significance_score: int | None
    comments_to_author: str | None
    confidential_comments_to_editor: str | None
    assigned_at: datetime
    submitted_at: datetime | None

    @classmethod
    def from_record(cls, record: ReviewAssignmentRecord) -> "ReviewOut":
        return cls(
            reviewer_id=UUID(str(record.reviewer_id)),
            status=record.status,
            recommendation=record.recommendation,
            originality_score=record.originality_score,
            rigour_score=record.rigour_score,
            clarity_score=record.clarity_score,
            significance_score=record.significance_score,
            comments_to_author=record.comments_to_author,
            confidential_comments_to_editor=record.confidential_comments_to_editor,
            assigned_at=record.assigned_at,
            submitted_at=record.submitted_at,
        )


class PersonOut(BaseModel):
    """An exact-email lookup's result — see `ugjcs.api.routers.people.lookup`.

    Deliberately absent: the email address itself. The caller already supplied it to
    make this match, and echoing it back would give this endpoint a second, harder to
    justify way to confirm which addresses have accounts."""

    id: UUID
    full_name: str
    affiliation: str

    @classmethod
    def from_domain(cls, account: Account) -> "PersonOut":
        return cls(
            id=UUID(str(account.id)), full_name=account.full_name, affiliation=account.affiliation
        )


class ReviewerCandidateOut(BaseModel):
    """One candidate reviewer for a manuscript, conflict-of-interest verdict included.

    `excluded_reason` is `None` for an eligible reviewer or a short human-readable
    string when they must not be assigned — see `ugjcs.domain.conflicts.exclusion_reason`,
    the pure function that decides it. Excluded candidates are returned in this list
    with their reason rather than filtered out, by design: see
    `ugjcs.api.routers.editorial.reviewer_candidates`.
    """

    id: UUID
    full_name: str
    affiliation: str
    active_assignments: int
    reviewer_capacity: int
    excluded_reason: str | None

    @classmethod
    def from_domain(
        cls, account: Account, *, active_assignments: int, excluded_reason: str | None
    ) -> "ReviewerCandidateOut":
        return cls(
            id=UUID(str(account.id)),
            full_name=account.full_name,
            affiliation=account.affiliation,
            active_assignments=active_assignments,
            reviewer_capacity=account.reviewer_capacity,
            excluded_reason=excluded_reason,
        )


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
    has_document: bool
    """Whether the published PDF can be downloaded — see FR-18 and
    `GET /archive/{tracking_code}/document`. Mirrors `ManuscriptOut.has_document`."""

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
            has_document=manuscript.original_document_key is not None,
        )
