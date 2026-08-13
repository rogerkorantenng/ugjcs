"""Hand-rolled PDF text-page machinery, shared by every module that authors a PDF.

`pypdf` has no page-authoring API of its own (it reads, merges and splits; it does not
lay out text), so this module writes a minimal PDF content stream by hand — a
`BT ... ET` text block using the built-in Helvetica base-14 fonts, which every PDF
viewer renders without an embedded font program — and lets `PdfWriter` handle the
container format around it.

Extracted from `demo_pdf.py` (which predates it and now imports from here) so that
`certificate_pdf.py` could reuse the same machinery instead of duplicating it. Both
callers do byte-level PDF assembly with `pypdf` and nothing else, which is why this
lives in the storage package's "PDF-authoring" corner beside `anonymize.py`.
"""

import textwrap
from collections.abc import Sequence

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, IndirectObject, NameObject

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0
MARGIN = 72.0
BODY_WIDTH_CHARS = 95
TITLE_WIDTH_CHARS = 60
TITLE_LINE_HEIGHT = 22.0
BODY_LINE_HEIGHT = 15.0
HEADING_GAP = 18.0

Line = tuple[str, float, float, str]
"""One absolutely positioned text line: (font resource name, size, baseline y, text)."""


def escape(text: str) -> str:
    """Escape the three bytes PDF string literals treat specially."""
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def font(base_font: str) -> DictionaryObject:
    result = DictionaryObject()
    result[NameObject("/Type")] = NameObject("/Font")
    result[NameObject("/Subtype")] = NameObject("/Type1")
    result[NameObject("/BaseFont")] = NameObject(f"/{base_font}")
    return result


def resources(regular: IndirectObject, bold: IndirectObject) -> DictionaryObject:
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = regular
    fonts[NameObject("/F2")] = bold
    result = DictionaryObject()
    result[NameObject("/Font")] = fonts
    return result


def render(lines: Sequence[Line]) -> bytes:
    """Turn `(font, size, y, text)` rows into a `BT ... ET` content stream.

    Each line is positioned with an absolute text matrix (`Tm`) rather than a relative
    move (`Td`), so a caller supplies the exact baseline it wants for every line instead
    of accumulating rounding drift across a paragraph.
    """
    parts = ["BT"]
    for font_name, size, y, text in lines:
        parts.append(f"/{font_name} {size:g} Tf")
        parts.append(f"1 0 0 1 {MARGIN:g} {y:g} Tm")
        parts.append(f"({escape(text)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def add_text_page(
    writer: PdfWriter,
    regular: IndirectObject,
    bold: IndirectObject,
    lines: Sequence[Line],
) -> None:
    page = writer.add_blank_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    page[NameObject("/Resources")] = resources(regular, bold)
    stream = DecodedStreamObject()
    stream.set_data(render(lines))
    page[NameObject("/Contents")] = writer._add_object(stream)


def wrap(text: str, width: int) -> list[str]:
    """`textwrap.wrap` that never collapses to an empty list for blank input."""
    return textwrap.wrap(text, width) or [text]
