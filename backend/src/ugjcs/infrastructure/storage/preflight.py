"""Anonymisation preflight: what the uploaded PDF carried before stripping.

An honest *partial* detector for the technical-debt register's TD-05 gap: DocInfo and
XMP metadata are reliably enumerated (they are structured), but author names in the
visible body text can only be found by substring search over `pypdf`'s extracted text —
which misses names split across lines, rendered as images, or spelled differently.
Empty `author_names_in_body` therefore means "nothing found", never "proven clean";
reliable text redaction remains out of scope, exactly as `anonymize.py` documents.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True, slots=True)
class PdfInspection:
    """What the anonymiser is about to remove (metadata) or cannot remove (body text)."""

    docinfo_keys: tuple[str, ...]
    """DocInfo keys present before stripping, e.g. `("/Author", "/Creator")`."""
    had_xmp: bool
    """Whether an XMP metadata stream was present (the anonymiser removes it either way)."""
    body_text: str
    """The concatenated per-page text `pypdf` could extract, for name scanning."""


def inspect_pdf(data: bytes) -> PdfInspection:
    """Parse `data` and report its DocInfo keys, XMP presence, and extractable text.

    Raises the same `pypdf` errors `strip_pdf_metadata` does on an unreadable file; the
    upload route already translates those into a 422 before anything is stored.
    """
    reader = PdfReader(BytesIO(data))
    metadata = reader.metadata
    keys = tuple(sorted(str(key) for key in metadata)) if metadata is not None else ()
    body_text = "\n".join(page.extract_text() for page in reader.pages)
    return PdfInspection(
        docinfo_keys=keys,
        had_xmp=reader.xmp_metadata is not None,
        body_text=body_text,
    )


def names_in_text(names: Iterable[str], text: str) -> list[str]:
    """Which of `names` appear as case-insensitive substrings of `text`, order kept.

    A substring check, deliberately simple: this is a red-flag detector for the
    submission response, not a redaction guarantee — see the module docstring.
    """
    haystack = text.casefold()
    found: list[str] = []
    for name in names:
        needle = name.strip().casefold()
        if needle and needle in haystack and name not in found:
            found.append(name)
    return found
