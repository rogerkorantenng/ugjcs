"""Wire shapes for the scholarly-record features: provenance, anonymisation preflight.

Kept apart from `schemas.py` so that file's established shapes stay untouched; the one
change made there (the derived `doi` field on `ArchivePaperOut`) is additive.
"""

from datetime import datetime
from typing import Self

from pydantic import BaseModel

from ugjcs.api.schemas import ManuscriptOut
from ugjcs.domain.manuscript import Manuscript


class ProvenanceEventOut(BaseModel):
    """One audit-chain link, projected for anonymous readers.

    Deliberately absent: the event payload and `actor_id` — payloads can reference
    reviewer identifiers (`REVIEW_SUBMITTED` records the reviewer as its actor), and a
    public endpoint must not hand out even a pseudonymous handle for them. Event type,
    timestamp and an 8-character hash prefix are enough to cross-check a published
    checkpoint without exposing who did what.
    """

    sequence: int
    event_type: str
    occurred_at: datetime
    hash_prefix: str


class ProvenanceOut(BaseModel):
    """The public verification summary of one manuscript's editorial event chain.

    `intact` means exactly what `ugjcs.domain.hashchain.verify` proves and no more:
    every stored link reconciles against a recomputation from the genesis hash. It
    cannot detect truncation of the tail, a forged event appended through the normal
    path, or a wholly fabricated history rebuilt from genesis — see that module's
    docstring for the external anchor those would need.
    """

    tracking_code: str
    intact: bool
    head_hash: str
    events: list[ProvenanceEventOut]


class AnonymisationReport(BaseModel):
    """What the anonymiser removed from the uploaded PDF, and what it could not.

    `author_names_in_body` is an honest partial detector for TD-05 (names printed in
    the visible body text survive metadata stripping): a case-insensitive substring
    scan of `pypdf`'s extracted text for the manuscript's authors' full names. An empty
    list means "nothing found", never "proven clean".
    """

    removed_docinfo_keys: list[str]
    xmp_removed: bool
    author_names_in_body: list[str]


class ManuscriptSubmissionOut(ManuscriptOut):
    """`ManuscriptOut` plus the anonymisation preflight report.

    A subclass, not a replacement: every existing `ManuscriptOut` consumer keeps every
    field it already relies on; submission and resubmission responses gain one extra
    top-level key.
    """

    anonymisation_report: AnonymisationReport

    @classmethod
    def from_submission(cls, manuscript: Manuscript, report: AnonymisationReport) -> Self:
        base = ManuscriptOut.from_domain(manuscript)
        return cls(**base.model_dump(), anonymisation_report=report)
