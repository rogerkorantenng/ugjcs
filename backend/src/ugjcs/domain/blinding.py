"""The reviewer-facing projection of a manuscript.

Blinding is structural: `BlindedManuscript` has no author attributes, so there is no
field a future change could accidentally populate. Filtering a full object would leave
that possibility open; omitting the fields from the type does not.
"""

from dataclasses import dataclass

from ugjcs.domain.manuscript import Manuscript


@dataclass(frozen=True, slots=True)
class BlindedManuscript:
    tracking_code: str
    title: str
    abstract: str
    keywords: tuple[str, ...]
    version: int
    status: str


def blind(manuscript: Manuscript) -> BlindedManuscript:
    """Project a manuscript into the form a reviewer is permitted to see."""
    return BlindedManuscript(
        tracking_code=manuscript.tracking_code.value,
        title=manuscript.title,
        abstract=manuscript.abstract,
        keywords=manuscript.keywords,
        version=manuscript.version,
        status=manuscript.status.value,
    )
