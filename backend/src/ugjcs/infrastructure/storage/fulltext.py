"""Extract a published PDF's text for the archive's full-text search.

Placed beside `preflight.py` because both do the same thing — run `pypdf`'s text
extraction over a manuscript PDF — but for different customers with different honesty
requirements: preflight scans for author names during submission, this feeds the
`manuscripts.fulltext` search column at publish time. The same caveat applies to both
and is restated here because search inherits it: `pypdf` extraction misses text
rendered as images and mangles unusual encodings, so an empty or partial result means
"this is what could be read", never "the document says nothing else".
"""

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(data: bytes) -> str:
    """The concatenated per-page text `pypdf` can extract, whitespace-normalised.

    Normalisation (split/join) collapses the layout-driven runs of spaces and newlines
    extraction produces, so the stored column feeds `to_tsvector` clean tokens and a
    `ts_headline` snippet reads as prose rather than as a ransom note of line breaks.
    Raises whatever `pypdf` raises on an unreadable file — the publish path catches and
    shrugs (search indexing must never block publication), the backfill logs and moves on.
    """
    reader = PdfReader(BytesIO(data))
    raw = "\n".join(page.extract_text() for page in reader.pages)
    return " ".join(raw.split())
