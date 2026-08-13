"""`extract_pdf_text` against a PDF this codebase itself authors, so the assertion is
about extraction, not about some checked-in binary fixture nobody can regenerate."""

import pytest
from pypdf.errors import PyPdfError

from ugjcs.infrastructure.storage.demo_pdf import build_demo_pdf
from ugjcs.infrastructure.storage.fulltext import extract_pdf_text


def test_extracts_title_and_body_text_whitespace_normalised() -> None:
    data = build_demo_pdf(
        tracking_code="SDJ-2026-0501",
        title="Solar Microgrid Load Forecasting",
        abstract="Forecasting village-level demand with gradient boosting.",
        keywords=("solar", "forecasting"),
        author_name="Ama Mensah",
    )
    text = extract_pdf_text(data)
    assert "Solar Microgrid Load Forecasting" in text
    assert "gradient boosting" in text
    assert "Introduction" in text  # the filler section pages are extracted too
    # Normalisation contract: single spaces only, so tsvector tokens and ts_headline
    # snippets are built from prose, not from layout artefacts.
    assert "\n" not in text
    assert "  " not in text


def test_an_unreadable_file_raises_for_the_caller_to_contain() -> None:
    """The publish hook and the backfill each decide their own containment; the
    extractor itself must stay honest and raise rather than answer ""."""
    with pytest.raises((PyPdfError, ValueError)):
        extract_pdf_text(b"%PDF-1.7 not actually a pdf")
