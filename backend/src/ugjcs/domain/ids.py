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

    @classmethod
    def mint(cls, year: int, sequence: int) -> Self:
        if sequence <= 0:
            raise ValueError("sequence must be positive")
        return cls(f"UGJCS-{year:04d}-{sequence:04d}")

    @classmethod
    def parse(cls, raw: str) -> Self:
        if not _TRACKING_PATTERN.match(raw):
            raise ValueError(f"malformed tracking code: {raw!r}")
        return cls(raw)
