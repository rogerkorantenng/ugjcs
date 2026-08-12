"""Editorial events — the append-only record of everything that happened.

Canonical serialisation is separated from hashing so that the byte representation
is testable on its own and stays stable if the hash algorithm is ever replaced.
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from ugjcs.domain.enums import EventType
from ugjcs.domain.ids import ManuscriptId, UserId

type PayloadValue = str | int | float | bool | None
"""Payload values are restricted to JSON-native scalars.

The hash chain in `hashchain.py` is only tamper-evident if equal events always
serialise to equal bytes. A `set` would serialise through its iteration order, which
varies with Python's per-process hash seed; an arbitrary object would fall back to a
`repr` containing a memory address. Either would make an untampered event fail
verification in a different process, which is a false tamper alert — worse than no
check at all. Restricting the type makes that unrepresentable.
"""


@dataclass(frozen=True, slots=True)
class EditorialEvent:
    manuscript_id: ManuscriptId
    sequence: int
    event_type: EventType
    payload: Mapping[str, PayloadValue]
    actor_id: UserId | None
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("sequence must be positive")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")

    def canonical_bytes(self) -> bytes:
        """A byte representation that is identical for equal events.

        Sorted keys and fixed separators make the encoding independent of dictionary
        insertion order, which is what allows the hash chain to be reproducible.
        """
        document = {
            "manuscript_id": str(self.manuscript_id),
            "sequence": self.sequence,
            "event_type": self.event_type.value,
            "payload": dict(self.payload),
            "actor_id": str(self.actor_id) if self.actor_id is not None else None,
            "occurred_at": self.occurred_at.isoformat(),
        }
        return json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
