"""Render an editorial decision certificate as a PDF.

Built with the same hand-rolled machinery `demo_pdf.py` uses (`pdf_text.py` and
`pdf_flow.py`) — no new dependency, no HTML-to-PDF engine. Reviews are labelled by
ordinal ("Reviewer 1"), never by name or identifier: the certificate may be forwarded
to authors, and the double-blind guarantee must survive that. Only `comments_to_author`
is printed; `confidential_comments_to_editor` never reaches this module at all — the
caller does not pass it, structurally, the same way `BlindedManuscriptOut` has no
author field.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfWriter

from ugjcs.infrastructure.storage.pdf_flow import LineFlow
from ugjcs.infrastructure.storage.pdf_text import (
    BODY_LINE_HEIGHT,
    BODY_WIDTH_CHARS,
    HEADING_GAP,
    TITLE_LINE_HEIGHT,
    TITLE_WIDTH_CHARS,
    add_text_page,
    font,
)

_MASTHEAD = (
    "Science and Development Journal - College of Basic and Applied Sciences, University of Ghana"
)


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """One review as the certificate shows it: content only, no reviewer identity."""

    recommendation: str | None
    originality_score: int | None
    rigour_score: int | None
    clarity_score: int | None
    significance_score: int | None
    comments_to_author: str | None


def _score(value: int | None) -> str:
    return str(value) if value is not None else "-"


def _review_lines(flow: LineFlow, ordinal: int, review: ReviewSummary) -> None:
    flow.gap(HEADING_GAP)
    flow.line("F2", 12.0, f"Reviewer {ordinal}", leading=HEADING_GAP)
    flow.line(
        "F1", 10.0, f"Recommendation: {review.recommendation or 'not recorded'}", leading=13.0
    )
    scores = (
        f"Scores (1-5): originality {_score(review.originality_score)}, "
        f"rigour {_score(review.rigour_score)}, clarity {_score(review.clarity_score)}, "
        f"significance {_score(review.significance_score)}"
    )
    flow.line("F1", 10.0, scores, leading=13.0)
    comments = review.comments_to_author or "none provided"
    flow.wrapped(
        "F1", 10.0, f"Comments to authors: {comments}", width=BODY_WIDTH_CHARS, leading=13.0
    )


def build_certificate_pdf(
    *,
    tracking_code: str,
    title: str,
    decision: str,
    rationale: str,
    reviews: Sequence[ReviewSummary],
    head_hash: str,
) -> bytes:
    """Return a certificate PDF: masthead, tracking code, title, decision with its
    rationale, each review by ordinal, and the audit-chain head hash as provenance."""
    flow = LineFlow()
    flow.line("F1", 10.0, _MASTHEAD, leading=TITLE_LINE_HEIGHT)
    flow.line("F2", 16.0, "Editorial Decision Certificate", leading=TITLE_LINE_HEIGHT)
    flow.gap(HEADING_GAP)
    flow.line("F1", 11.0, f"Tracking code: {tracking_code}", leading=BODY_LINE_HEIGHT)
    flow.wrapped("F2", 13.0, title, width=TITLE_WIDTH_CHARS, leading=HEADING_GAP)
    flow.gap(HEADING_GAP)
    flow.line("F2", 12.0, f"Decision: {decision}", leading=HEADING_GAP)
    flow.wrapped(
        "F1", 11.0, f"Rationale: {rationale}", width=BODY_WIDTH_CHARS, leading=BODY_LINE_HEIGHT
    )
    for ordinal, review in enumerate(reviews, start=1):
        _review_lines(flow, ordinal, review)
    flow.gap(HEADING_GAP)
    flow.line("F1", 9.0, f"Provenance: audit-chain head hash {head_hash}", leading=BODY_LINE_HEIGHT)

    writer = PdfWriter()
    regular = writer._add_object(font("Helvetica"))
    bold = writer._add_object(font("Helvetica-Bold"))
    for lines in flow.pages():
        add_text_page(writer, regular, bold, lines)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
