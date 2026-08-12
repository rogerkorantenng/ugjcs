"""Typed identifiers.

`NewType` gives compile-time separation between identifier kinds at zero runtime cost,
so a `UserId` can never be passed where a `ManuscriptId` is expected.
"""

import re
from dataclasses import dataclass
from typing import NewType, Self
from uuid import UUID

UserId = NewType("UserId", UUID)
ManuscriptId = NewType("ManuscriptId", UUID)
ReviewId = NewType("ReviewId", UUID)
IssueId = NewType("IssueId", UUID)

_TRACKING_PATTERN = re.compile(r"^UGJCS-(\d{4})-(\d{4,})$")


@dataclass(frozen=True, slots=True)
class TrackingCode:
    """The human-facing reference an author quotes in correspondence."""

    value: str

    def __post_init__(self) -> None:
        """Validate in the constructor so no path can produce a code `parse` rejects."""
        if not _TRACKING_PATTERN.match(self.value):
            raise ValueError(f"malformed tracking code: {self.value!r}")

    @classmethod
    def mint(cls, year: int, sequence: int) -> Self:
        if not 1000 <= year <= 9999:
            raise ValueError("year must be four digits")
        if sequence <= 0:
            raise ValueError("sequence must be positive")
        return cls(f"UGJCS-{year:04d}-{sequence:04d}")

    @classmethod
    def parse(cls, raw: str) -> Self:
        """Construct from an externally supplied string.

        Validation now lives in `__post_init__`, so this is a thin wrapper; it is kept
        for the explicit name at call sites reading untrusted input.
        """
        return cls(raw)
