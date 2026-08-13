from io import BytesIO

from pypdf import PdfReader

from ugjcs.infrastructure.storage.anonymize import strip_pdf_metadata
from ugjcs.infrastructure.storage.demo_pdf import build_demo_pdf

_TITLE = "Sparse Retrieval for Low-Resource Languages"
_ABSTRACT = (
    "We study sparse lexical retrieval for Twi and Ga, two Ghanaian languages with "
    "little annotated text, and show that morphology-aware tokenisation narrows most "
    "of the gap to a dense retriever trained on English."
)


def _build(author_name: str = "Ama Serwaa") -> bytes:
    return build_demo_pdf(
        tracking_code="SDJ-2026-000001",
        title=_TITLE,
        abstract=_ABSTRACT,
        keywords=("information retrieval", "low-resource NLP"),
        author_name=author_name,
    )


def test_it_produces_a_well_formed_multi_page_pdf() -> None:
    data = _build()
    assert data.startswith(b"%PDF")
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) >= 2


def test_the_first_page_carries_the_title_and_abstract_as_visible_text() -> None:
    data = _build()
    text = PdfReader(BytesIO(data)).pages[0].extract_text()
    assert "Sparse Retrieval for Low-Resource Languages" in text
    assert "morphology-aware tokenisation" in text
    assert "Abstract" in text


def test_the_tracking_code_appears_on_the_first_page() -> None:
    data = _build()
    text = PdfReader(BytesIO(data)).pages[0].extract_text()
    assert "SDJ-2026-000001" in text


def test_author_and_creator_docinfo_carry_the_authors_real_name() -> None:
    data = _build(author_name="Ama Serwaa")
    metadata = PdfReader(BytesIO(data)).metadata
    assert metadata is not None
    assert metadata.author == "Ama Serwaa"
    assert metadata.creator == "Ama Serwaa"


def test_the_author_name_survives_into_the_raw_bytes_so_anonymisation_has_something_to_strip() -> (
    None
):
    data = _build(author_name="Ama Serwaa")
    assert b"Ama Serwaa" in data

    anonymised = strip_pdf_metadata(data)
    assert b"Ama Serwaa" not in anonymised
    metadata = PdfReader(BytesIO(anonymised)).metadata
    assert metadata is not None
    assert metadata.author is None


def test_the_anonymised_derivative_still_shows_the_title_and_abstract() -> None:
    anonymised = strip_pdf_metadata(_build())
    text = PdfReader(BytesIO(anonymised)).pages[0].extract_text()
    assert "Sparse Retrieval for Low-Resource Languages" in text


def test_a_manuscript_with_no_keywords_still_builds_cleanly() -> None:
    data = build_demo_pdf(
        tracking_code="SDJ-2026-000002",
        title=_TITLE,
        abstract=_ABSTRACT,
        keywords=(),
        author_name="Kojo Antwi",
    )
    assert data.startswith(b"%PDF")


def test_a_very_long_title_and_abstract_still_produce_a_valid_document() -> None:
    long_title = "A " + "Very " * 40 + "Long Title"
    long_abstract = "Sentence about the study. " * 60
    data = build_demo_pdf(
        tracking_code="SDJ-2026-000003",
        title=long_title,
        abstract=long_abstract,
        keywords=("a", "b", "c"),
        author_name="Adjoa Boadi",
    )
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) >= 2
