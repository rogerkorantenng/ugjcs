"""Typed identifiers.

`NewType` gives compile-time separation between identifier kinds at zero runtime cost,
so a `UserId` can never be passed where a `ManuscriptId` is expected.
"""

import re
from dataclasses import dataclass
from typing import NewType, Self
from uuid import NAMESPACE_URL, UUID, uuid5

UserId = NewType("UserId", UUID)
ManuscriptId = NewType("ManuscriptId", UUID)
ReviewId = NewType("ReviewId", UUID)
IssueId = NewType("IssueId", UUID)

_ISSUE_NAMESPACE = uuid5(NAMESPACE_URL, "https://ugjcs.example.edu/issues")


def mint_issue_id(volume: int, number: int) -> IssueId:
    """Derive a stable `IssueId` for (volume, number), with no `Issue` entity to look up.

    Issues are not modelled as a persisted entity (Plan 1's scope decision, unchanged
    since). Scheduling still needs *some* identifier, and the choice here is a
    deterministic one over accepting an arbitrary client-supplied UUID: the same
    `(volume, number)` always mints the same id, so every manuscript scheduled into
    "volume 3, number 1" lands under one shared identifier without a table to enforce
    it, and a client cannot accidentally (or deliberately) fragment one issue into two
    ids by typo. `uuid5` over a fixed namespace makes this reproducible across processes,
    unlike `uuid4` or `hash()`, which are exactly the two ways that guarantee would break.
    """
    if volume <= 0 or number <= 0:
        raise ValueError("volume and number must be positive")
    return IssueId(uuid5(_ISSUE_NAMESPACE, f"{volume}.{number}"))


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
