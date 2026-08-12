from uuid import uuid4

import pytest

from ugjcs.application.documents import (
    MAX_DOCUMENT_BYTES,
    DocumentTooLargeError,
    UnsupportedDocumentTypeError,
    anonymised_key,
    original_key,
    validate_document,
)
from ugjcs.domain.ids import ManuscriptId

MANUSCRIPT_ID = ManuscriptId(uuid4())


def test_a_well_formed_pdf_passes_validation() -> None:
    validate_document(b"%PDF-1.4\n...\n%%EOF")


def test_content_not_beginning_with_the_pdf_magic_number_is_rejected() -> None:
    with pytest.raises(UnsupportedDocumentTypeError):
        validate_document(b"this is not a pdf at all")


def test_an_empty_upload_is_rejected() -> None:
    with pytest.raises(UnsupportedDocumentTypeError):
        validate_document(b"")


def test_a_client_supplied_content_type_cannot_substitute_for_the_magic_number() -> None:
    """The whole point of FR-05: validation reads bytes, not a claim about them. This
    function takes no content-type argument at all, so there is nothing a caller could
    even pass to bypass the check."""
    with pytest.raises(UnsupportedDocumentTypeError):
        validate_document(b"<html>not a pdf, whatever the client claimed</html>")


def test_content_exceeding_the_size_cap_is_rejected() -> None:
    oversized = b"%PDF-1.4" + b"0" * MAX_DOCUMENT_BYTES
    with pytest.raises(DocumentTooLargeError):
        validate_document(oversized)


def test_content_exactly_at_the_size_cap_is_accepted() -> None:
    exactly_at_cap = b"%PDF-1.4" + b"0" * (MAX_DOCUMENT_BYTES - len(b"%PDF-1.4"))
    assert len(exactly_at_cap) == MAX_DOCUMENT_BYTES
    validate_document(exactly_at_cap)


def test_original_and_anonymised_keys_differ_for_the_same_manuscript_and_version() -> None:
    original = original_key(MANUSCRIPT_ID, version=1)
    anonymised = anonymised_key(MANUSCRIPT_ID, version=1)
    assert original != anonymised
    assert str(MANUSCRIPT_ID) in original
    assert str(MANUSCRIPT_ID) in anonymised


def test_keys_carry_no_title_or_author_identifying_text() -> None:
    """Only the manuscript's opaque UUID and version number appear in the key — the
    requirement that the key "does not leak identity"."""
    key = original_key(MANUSCRIPT_ID, version=3)
    assert key == f"manuscripts/{MANUSCRIPT_ID}/v3/original.pdf"


def test_different_versions_of_the_same_manuscript_get_different_keys() -> None:
    assert original_key(MANUSCRIPT_ID, version=1) != original_key(MANUSCRIPT_ID, version=2)
