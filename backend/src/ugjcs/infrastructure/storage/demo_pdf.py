"""Build a plausible, multi-page PDF for a seeded demonstration manuscript.

Exists for exactly one caller, `ugjcs.scripts.seed_demo`: every manuscript the seed
drives through the editorial lifecycle needs a real document, not a blank sheet. The
byte-level page assembly lives in `pdf_text.py`, shared with `certificate_pdf.py`;
this module only decides *what* a demonstration manuscript's pages say. Placed beside
`anonymize.py` because both do byte-level PDF surgery with `pypdf` and nothing else.
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

# Placeholder body text for the filler pages after the title page, so a reviewer sees
# something manuscript-shaped rather than an abstract stapled to blank paper.
# Content-free by design: this is a demonstration artefact, not a real submission.
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
    """Return a small multi-page PDF: a title page carrying `title`/`abstract`, filler
    section pages, and `/Author`/`/Creator` DocInfo set to `author_name`.

    The DocInfo assignment is the point, not an afterthought: `strip_pdf_metadata`
    removes exactly these fields, and a demonstration corpus whose PDFs never carried
    an author name would make the anonymisation feature invisible.
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

    writer.add_metadata({"/Title": title, "/Author": author_name, "/Creator": author_name})
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
