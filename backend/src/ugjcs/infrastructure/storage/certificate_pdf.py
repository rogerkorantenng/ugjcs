"""Render an editorial decision certificate as a PDF.

Built with the same hand-rolled machinery `demo_pdf.py` uses (`pdf_text.py`) — no new
dependency, no HTML-to-PDF engine. Reviews are labelled by ordinal ("Reviewer 1"),
never by name or identifier: the certificate may be forwarded to authors, and the
double-blind guarantee must survive that. Only `comments_to_author` is printed;
`confidential_comments_to_editor` never reaches this module at all — the caller does
not pass it, structurally, the same way `BlindedManuscriptOut` has no author field.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfWriter

from ugjcs.infrastructure.storage.pdf_text import (
    BODY_LINE_HEIGHT,
    BODY_WIDTH_CHARS,
    HEADING_GAP,
    MARGIN,
    PAGE_HEIGHT,
    TITLE_LINE_HEIGHT,
    TITLE_WIDTH_CHARS,
    Line,
    add_text_page,
    font,
    wrap,
)

_MASTHEAD = (
    "Science and Development Journal - College of Basic and Applied Sciences, "
    "University of Ghana"
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


class _Flow:
    """Accumulate lines top to bottom, breaking to a new page at the bottom margin."""

    def __init__(self) -> None:
        self._pages: list[list[Line]] = []
        self._lines: list[Line] = []
        self._y = PAGE_HEIGHT - MARGIN

    def line(self, font_name: str, size: float, text: str, *, leading: float) -> None:
        if self._y < MARGIN:
            self._pages.append(self._lines)
            self._lines = []
            self._y = PAGE_HEIGHT - MARGIN
        self._lines.append((font_name, size, self._y, text))
        self._y -= leading

    def wrapped(
        self, font_name: str, size: float, text: str, *, width: int, leading: float
    ) -> None:
        for piece in wrap(text, width):
            self.line(font_name, size, piece, leading=leading)

    def gap(self, amount: float = HEADING_GAP) -> None:
        self._y -= amount

    def pages(self) -> list[list[Line]]:
        return [*self._pages, self._lines] if self._lines else list(self._pages)


def _score(value: int | None) -> str:
    return str(value) if value is not None else "-"


def _review_lines(flow: _Flow, ordinal: int, review: ReviewSummary) -> None:
    flow.gap()
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
    flow = _Flow()
    flow.line("F1", 10.0, _MASTHEAD, leading=TITLE_LINE_HEIGHT)
    flow.line("F2", 16.0, "Editorial Decision Certificate", leading=TITLE_LINE_HEIGHT)
    flow.gap()
    flow.line("F1", 11.0, f"Tracking code: {tracking_code}", leading=BODY_LINE_HEIGHT)
    flow.wrapped("F2", 13.0, title, width=TITLE_WIDTH_CHARS, leading=HEADING_GAP)
    flow.gap()
    flow.line("F2", 12.0, f"Decision: {decision}", leading=HEADING_GAP)
    flow.wrapped(
        "F1", 11.0, f"Rationale: {rationale}", width=BODY_WIDTH_CHARS, leading=BODY_LINE_HEIGHT
    )
    for ordinal, review in enumerate(reviews, start=1):
        _review_lines(flow, ordinal, review)
    flow.gap()
    flow.line("F1", 9.0, f"Provenance: audit-chain head hash {head_hash}", leading=BODY_LINE_HEIGHT)

    writer = PdfWriter()
    regular = writer._add_object(font("Helvetica"))
    bold = writer._add_object(font("Helvetica-Bold"))
    for lines in flow.pages():
        add_text_page(writer, regular, bold, lines)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
