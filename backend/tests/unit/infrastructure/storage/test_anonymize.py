from io import BytesIO

from pypdf import PdfReader, PdfWriter

from ugjcs.infrastructure.storage.anonymize import strip_pdf_metadata


def _pdf_with_author(name: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_metadata({"/Author": name, "/Title": "A Title"})
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_strips_the_author_from_docinfo() -> None:
    original = _pdf_with_author("Roger Koranteng Obeng")
    assert b"Roger Koranteng Obeng" in original

    stripped = strip_pdf_metadata(original)
    assert b"Roger Koranteng Obeng" not in stripped


def test_the_stripped_document_still_has_the_same_page_count() -> None:
    original = _pdf_with_author("Someone")
    stripped = strip_pdf_metadata(original)
    assert len(PdfReader(BytesIO(stripped)).pages) == len(PdfReader(BytesIO(original)).pages)


def test_docinfo_is_cleared_not_merely_overwritten_with_a_default() -> None:
    stripped = strip_pdf_metadata(_pdf_with_author("Someone"))
    metadata = PdfReader(BytesIO(stripped)).metadata
    assert metadata is not None
    assert metadata.author is None
    assert metadata.title is None


def test_a_document_with_no_metadata_at_all_still_strips_cleanly() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = BytesIO()
    writer.write(buffer)
    stripped = strip_pdf_metadata(buffer.getvalue())
    assert len(PdfReader(BytesIO(stripped)).pages) == 1
