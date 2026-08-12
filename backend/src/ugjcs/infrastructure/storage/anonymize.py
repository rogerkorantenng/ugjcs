"""Produce the reviewer-facing derivative of a manuscript PDF.

What this strips: the `/Info` dictionary (DocInfo — author, title, producer, creation
tool, timestamps) and any XMP metadata stream, both of which routinely carry an author's
real name even when the manuscript body itself is anonymised.

What this does NOT do, stated plainly so no caller assumes more than it provides: it
cannot detect or remove an author's name printed in the visible body text, a running
header, or a footer — reliable text redaction is a research problem, not a metadata
operation. That gap is `docs/04-technical-debt-register.md`'s **TD-05**, the same
limitation `ugjcs.domain.blinding` already documents for the title/abstract/keywords
fields it copies verbatim; this module closes the metadata half of the exposure, not the
body-text half.
"""

from io import BytesIO

from pypdf import PdfReader, PdfWriter


def strip_pdf_metadata(data: bytes) -> bytes:
    """Return a byte-for-byte-different PDF with DocInfo and XMP metadata removed.

    Rebuilds the document page by page into a fresh `PdfWriter` rather than mutating the
    reader in place, so no metadata dictionary the reader parsed but did not walk into
    (some viewers write vendor-specific metadata streams pypdf does not enumerate by
    name) survives by omission.
    """
    reader = PdfReader(BytesIO(data))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({})
    writer.xmp_metadata = None
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
