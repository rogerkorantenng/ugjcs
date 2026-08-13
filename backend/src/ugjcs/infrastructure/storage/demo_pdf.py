"""Build a plausible, multi-page PDF for a seeded demonstration manuscript.

Exists for exactly one caller, `ugjcs.scripts.seed_demo`: the seed script predates file
upload, so every manuscript it drives through the editorial lifecycle needs a real
document to attach, not a blank sheet. The byte-level page assembly (content streams,
base-14 fonts) lives in `pdf_text.py`, shared with `certificate_pdf.py`; this module
only decides *what* a demonstration manuscript's pages say.

Deliberately placed beside `anonymize.py`, not in `ugjcs.scripts`: both modules do
byte-level PDF surgery with `pypdf` and nothing else, so they belong to the same
"PDF-authoring" corner of the storage package rather than to the seed script's own
business logic (which orchestrates *what* gets built and *when*, not *how* a PDF is
assembled).
"""

from collections.abc import Sequence
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


def _title_page_lines(
    *, tracking_code: str, title: str, abstract: str, keywords: Sequence[str]
) -> list[Line]:
    lines: list[Line] = []
    y = PAGE_HEIGHT - MARGIN
    header = f"Science and Development Journal (CBAS, University of Ghana)  -  {tracking_code}"
    lines.append(("F1", 10.0, y, header))
    y -= TITLE_LINE_HEIGHT
    for wrapped in wrap(title, TITLE_WIDTH_CHARS):
        lines.append(("F2", 16.0, y, wrapped))
        y -= TITLE_LINE_HEIGHT
    y -= HEADING_GAP - TITLE_LINE_HEIGHT
    lines.append(("F2", 12.0, y, "Abstract"))
    y -= HEADING_GAP
    for wrapped in wrap(abstract, BODY_WIDTH_CHARS):
        lines.append(("F1", 11.0, y, wrapped))
        y -= BODY_LINE_HEIGHT
    if keywords:
        y -= HEADING_GAP - BODY_LINE_HEIGHT
        keyword_line = "Keywords: " + ", ".join(keywords)
        for wrapped in wrap(keyword_line, BODY_WIDTH_CHARS):
            lines.append(("F1", 10.0, y, wrapped))
            y -= BODY_LINE_HEIGHT
    return lines


def _filler_page_lines(*, heading: str, body: str) -> list[Line]:
    lines: list[Line] = []
    y = PAGE_HEIGHT - MARGIN
    lines.append(("F2", 13.0, y, heading))
    y -= HEADING_GAP
    for wrapped in wrap(body, BODY_WIDTH_CHARS):
        lines.append(("F1", 11.0, y, wrapped))
        y -= BODY_LINE_HEIGHT
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
    regular = writer._add_object(font("Helvetica"))
    bold = writer._add_object(font("Helvetica-Bold"))

    add_text_page(
        writer,
        regular,
        bold,
        _title_page_lines(
            tracking_code=tracking_code, title=title, abstract=abstract, keywords=keywords
        ),
    )
    for heading, body in _FILLER_SECTIONS:
        add_text_page(writer, regular, bold, _filler_page_lines(heading=heading, body=body))

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
