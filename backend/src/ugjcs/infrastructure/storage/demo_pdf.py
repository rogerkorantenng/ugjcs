"""Build a plausible, multi-page PDF for a seeded demonstration manuscript.

Exists for exactly one caller, `ugjcs.scripts.seed_demo`: the seed script predates file
upload, so every manuscript it drives through the editorial lifecycle needs a real
document to attach, not a blank sheet. `pypdf` has no page-authoring API of its own (it
reads, merges and splits; it does not lay out text), so this module writes a minimal PDF
content stream by hand — a `BT ... ET` text block using the built-in Helvetica base-14
font, which every PDF viewer renders without an embedded font program — and lets
`PdfWriter` handle the container format around it.

Deliberately placed beside `anonymize.py`, not in `ugjcs.scripts`: both modules do
byte-level PDF surgery with `pypdf` and nothing else, so they belong to the same
"PDF-authoring" corner of the storage package rather than to the seed script's own
business logic (which orchestrates *what* gets built and *when*, not *how* a PDF is
assembled).
"""

import textwrap
from collections.abc import Sequence
from io import BytesIO

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, IndirectObject, NameObject

_PAGE_WIDTH = 612.0
_PAGE_HEIGHT = 792.0
_MARGIN = 72.0
_BODY_WIDTH_CHARS = 95
_TITLE_WIDTH_CHARS = 60
_TITLE_LINE_HEIGHT = 22.0
_BODY_LINE_HEIGHT = 15.0
_HEADING_GAP = 18.0

# Placeholder body-section text for the filler pages that follow the title page, so a
# reviewer sees a document that looks like a manuscript in progress rather than an
# abstract stapled to blank paper. Content-free by design: this is a demonstration
# artefact, not a real submission, and its wording is irrelevant to what it needs to
# prove (that a document exists, carries the right title/abstract, and can be
# anonymised).
_FILLER_SECTIONS: tuple[tuple[str, str], ...] = (
    (
        "1. Introduction",
        "This section motivates the study, situates it against prior work, and states the "
        "research questions addressed in the remainder of the manuscript. It is placeholder "
        "text generated for demonstration purposes and does not describe real experiments.",
    ),
    (
        "2. Methodology",
        "This section would ordinarily describe the data, models and evaluation protocol "
        "used to obtain the results summarised in the abstract. It is placeholder text "
        "generated for demonstration purposes and does not describe a real methodology.",
    ),
)


def _escape(text: str) -> str:
    """Escape the three bytes PDF string literals treat specially."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _font(base_font: str) -> DictionaryObject:
    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject(f"/{base_font}")
    return font


def _resources(regular: IndirectObject, bold: IndirectObject) -> DictionaryObject:
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = regular
    fonts[NameObject("/F2")] = bold
    resources = DictionaryObject()
    resources[NameObject("/Font")] = fonts
    return resources


def _render(lines: Sequence[tuple[str, float, float, str]]) -> bytes:
    """Turn `(font, size, y, text)` rows into a `BT ... ET` content stream.

    Each line is positioned with an absolute text matrix (`Tm`) rather than a relative
    move (`Td`), so a caller supplies the exact baseline it wants for every line instead
    of accumulating rounding drift across a paragraph.
    """
    parts = ["BT"]
    for font, size, y, text in lines:
        parts.append(f"/{font} {size:g} Tf")
        parts.append(f"1 0 0 1 {_MARGIN:g} {y:g} Tm")
        parts.append(f"({_escape(text)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def _add_text_page(
    writer: PdfWriter,
    regular: IndirectObject,
    bold: IndirectObject,
    lines: Sequence[tuple[str, float, float, str]],
) -> None:
    page = writer.add_blank_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    page[NameObject("/Resources")] = _resources(regular, bold)
    stream = DecodedStreamObject()
    stream.set_data(_render(lines))
    page[NameObject("/Contents")] = writer._add_object(stream)


def _title_page_lines(
    *, tracking_code: str, title: str, abstract: str, keywords: Sequence[str]
) -> list[tuple[str, float, float, str]]:
    lines: list[tuple[str, float, float, str]] = []
    y = _PAGE_HEIGHT - _MARGIN
    header = f"Science and Development Journal (CBAS, University of Ghana)  -  {tracking_code}"
    lines.append(("F1", 10.0, y, header))
    y -= _TITLE_LINE_HEIGHT
    for wrapped in textwrap.wrap(title, _TITLE_WIDTH_CHARS) or [title]:
        lines.append(("F2", 16.0, y, wrapped))
        y -= _TITLE_LINE_HEIGHT
    y -= _HEADING_GAP - _TITLE_LINE_HEIGHT
    lines.append(("F2", 12.0, y, "Abstract"))
    y -= _HEADING_GAP
    for wrapped in textwrap.wrap(abstract, _BODY_WIDTH_CHARS) or [abstract]:
        lines.append(("F1", 11.0, y, wrapped))
        y -= _BODY_LINE_HEIGHT
    if keywords:
        y -= _HEADING_GAP - _BODY_LINE_HEIGHT
        keyword_line = "Keywords: " + ", ".join(keywords)
        for wrapped in textwrap.wrap(keyword_line, _BODY_WIDTH_CHARS) or [keyword_line]:
            lines.append(("F1", 10.0, y, wrapped))
            y -= _BODY_LINE_HEIGHT
    return lines


def _filler_page_lines(*, heading: str, body: str) -> list[tuple[str, float, float, str]]:
    lines: list[tuple[str, float, float, str]] = []
    y = _PAGE_HEIGHT - _MARGIN
    lines.append(("F2", 13.0, y, heading))
    y -= _HEADING_GAP
    for wrapped in textwrap.wrap(body, _BODY_WIDTH_CHARS) or [body]:
        lines.append(("F1", 11.0, y, wrapped))
        y -= _BODY_LINE_HEIGHT
    return lines


def build_demo_pdf(
    *,
    tracking_code: str,
    title: str,
    abstract: str,
    keywords: Sequence[str],
    author_name: str,
) -> bytes:
    """Return a small multi-page PDF: a title page carrying `title`/`abstract`, followed
    by placeholder section pages, with `/Author` and `/Creator` DocInfo set to
    `author_name`.

    That DocInfo assignment is the point of this function's second half, not an
    afterthought: `infrastructure.storage.anonymize.strip_pdf_metadata` produces the
    reviewer-facing derivative by removing exactly these fields, so a demonstration
    corpus whose source PDFs never carried an author name in the first place would make
    the anonymisation feature invisible — there would be nothing in the original for the
    derivative to visibly differ from.
    """
    writer = PdfWriter()
    regular = writer._add_object(_font("Helvetica"))
    bold = writer._add_object(_font("Helvetica-Bold"))

    _add_text_page(
        writer,
        regular,
        bold,
        _title_page_lines(
            tracking_code=tracking_code, title=title, abstract=abstract, keywords=keywords
        ),
    )
    for heading, body in _FILLER_SECTIONS:
        _add_text_page(writer, regular, bold, _filler_page_lines(heading=heading, body=body))

    writer.add_metadata(
        {
            "/Title": title,
            "/Author": author_name,
            "/Creator": author_name,
        }
    )
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
