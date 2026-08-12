"""Tamper-evident chaining over the editorial event log.

Each event's hash covers its predecessor's hash, so altering, reordering or removing an
event in the interior of the chain invalidates every hash after it. This detects
tampering; it does not prevent it, which is why the database also denies UPDATE and
DELETE on the event table.

What this construction cannot detect on its own, stated plainly so no caller assumes
more than it provides:

- Truncation of the tail. Any prefix of a valid chain is itself a valid chain.
- A forged event appended through `append`, which is indistinguishable from a genuine one.
- A wholly fabricated history rebuilt from the genesis hash using these same functions.

All three need an external anchor the forger cannot reproduce: a periodically published
or signed checkpoint of the latest `event_hash`, plus an expected event count asserted at
the persistence boundary. That anchor is out of scope for the domain layer and is
recorded in the technical debt register.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from ugjcs.domain.errors import DomainError
from ugjcs.domain.events import EditorialEvent

GENESIS_HASH = "0" * 64


class ChainBrokenError(DomainError):
    """The event chain does not verify against its recorded hashes."""


@dataclass(frozen=True, slots=True)
class ChainedEvent:
    event: EditorialEvent
    previous_hash: str
    event_hash: str


def chain_hash(event: EditorialEvent, previous_hash: str) -> str:
    """SHA-256 over the predecessor hash followed by the event's canonical bytes."""
    digest = hashlib.sha256()
    digest.update(previous_hash.encode("ascii"))
    digest.update(event.canonical_bytes())
    return digest.hexdigest()


def append(chain: Sequence[ChainedEvent], event: EditorialEvent) -> ChainedEvent:
    """Link `event` onto the end of `chain`, enforcing consecutive sequencing."""
    expected_sequence = len(chain) + 1
    if event.sequence != expected_sequence:
        raise ChainBrokenError(f"expected sequence {expected_sequence}, received {event.sequence}")
    previous_hash = chain[-1].event_hash if chain else GENESIS_HASH
    return ChainedEvent(
        event=event,
        previous_hash=previous_hash,
        event_hash=chain_hash(event, previous_hash),
    )


def verify(chain: Sequence[ChainedEvent]) -> None:
    """Raise `ChainBrokenError` at the first link that does not reconcile."""
    previous_hash = GENESIS_HASH
    for position, link in enumerate(chain, start=1):
        if link.event.sequence != position:
            raise ChainBrokenError(f"expected sequence {position}, found {link.event.sequence}")
        if link.previous_hash != previous_hash:
            raise ChainBrokenError(f"broken link at sequence {link.event.sequence}")
        if chain_hash(link.event, previous_hash) != link.event_hash:
            raise ChainBrokenError(f"hash mismatch at sequence {link.event.sequence}")
        previous_hash = link.event_hash
