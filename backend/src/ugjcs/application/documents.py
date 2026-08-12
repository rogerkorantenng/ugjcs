"""Manuscript document upload: validation and object-storage key naming.

Pure logic over bytes and identifiers — no `boto3`, no filesystem, no network. The S3
adapter that actually moves bytes lives in `infrastructure.storage`; this module is what
decides whether an upload is acceptable and where it belongs, independent of how it is
eventually stored.
"""

from datetime import timedelta

from ugjcs.domain.errors import DomainError
from ugjcs.domain.ids import ManuscriptId

PRESIGNED_URL_TTL = timedelta(minutes=5)
"""How long a document's pre-signed URL stays valid. Short enough that a leaked link (a
forwarded email, a browser history entry) is useless within the hour; long enough that a
reviewer's page load and the file download it triggers both finish inside one window."""

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
"""10 MB. Generous for a typeset manuscript PDF, small enough that an upload cannot be
used to exhaust storage or the request body buffer."""

PDF_MAGIC = b"%PDF"
"""The first four bytes of every PDF file, per ISO 32000. Checked against the content
itself, never against a filename extension or the client-supplied `Content-Type` header —
either of those is trivially forged by a client that wants to smuggle something else past
this check."""


class UnsupportedDocumentTypeError(DomainError):
    """The uploaded bytes do not begin with the PDF magic number."""


class DocumentTooLargeError(DomainError):
    """The uploaded bytes exceed `MAX_DOCUMENT_BYTES`."""


def validate_document(data: bytes) -> None:
    """Raise unless `data` is a plausible PDF within the size cap.

    Order matters: size is cheap to check and rejects the more common accident (someone
    attaching an enormous file) before spending a comparison on content; the magic-byte
    check catches everything else, including a well-formed non-PDF and an empty upload.
    """
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DocumentTooLargeError(
            f"document exceeds the {MAX_DOCUMENT_BYTES} byte limit ({len(data)} bytes)"
        )
    if not data.startswith(PDF_MAGIC):
        raise UnsupportedDocumentTypeError("document does not begin with the PDF magic number")


def original_key(manuscript_id: ManuscriptId, *, version: int) -> str:
    """The storage key for this version's unmodified upload.

    Keyed on the manuscript's opaque UUID and version, never on its title, tracking code
    or any author's name — nothing in the key itself identifies who wrote the document or
    what it is about.
    """
    return f"manuscripts/{manuscript_id}/v{version}/original.pdf"


def anonymised_key(manuscript_id: ManuscriptId, *, version: int) -> str:
    """The storage key for this version's metadata-stripped derivative."""
    return f"manuscripts/{manuscript_id}/v{version}/anonymised.pdf"
