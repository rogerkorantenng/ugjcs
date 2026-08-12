from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import EventType
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import (
    GENESIS_HASH,
    ChainBrokenError,
    ChainedEvent,
    append,
    chain_hash,
    verify,
)
from ugjcs.domain.ids import ManuscriptId, UserId

MANUSCRIPT = ManuscriptId(uuid4())


def event(sequence: int, **payload: PayloadValue) -> EditorialEvent:
    return EditorialEvent(
        manuscript_id=MANUSCRIPT,
        sequence=sequence,
        event_type=EventType.DECISION_RECORDED,
        payload=payload or {"note": "ok"},
        actor_id=UserId(uuid4()),
        occurred_at=datetime(2026, 8, 12, 10, sequence, tzinfo=UTC),
    )


def build_chain(length: int) -> list[ChainedEvent]:
    chain: list[ChainedEvent] = []
    for sequence in range(1, length + 1):
        chain.append(append(chain, event(sequence)))
    return chain


def test_hash_is_sixty_four_hex_characters() -> None:
    digest = chain_hash(event(1), GENESIS_HASH)
    assert len(digest) == 64
    assert all(character in "0123456789abcdef" for character in digest)


def test_first_event_chains_from_genesis() -> None:
    chain = build_chain(1)
    assert chain[0].previous_hash == GENESIS_HASH


def test_each_event_chains_to_its_predecessor() -> None:
    chain = build_chain(3)
    assert chain[1].previous_hash == chain[0].event_hash
    assert chain[2].previous_hash == chain[1].event_hash


def test_identical_payloads_at_different_positions_hash_differently() -> None:
    chain = build_chain(2)
    assert chain[0].event_hash != chain[1].event_hash


def test_verify_accepts_an_untampered_chain() -> None:
    verify(build_chain(4))


def test_verify_accepts_an_empty_chain() -> None:
    verify([])


def test_verify_detects_a_modified_payload() -> None:
    chain = build_chain(3)
    chain[1] = replace(chain[1], event=event(2, note="tampered"))
    with pytest.raises(ChainBrokenError, match="sequence 2"):
        verify(chain)


def test_verify_detects_a_removed_event() -> None:
    chain = build_chain(3)
    del chain[1]
    with pytest.raises(ChainBrokenError):
        verify(chain)


def test_verify_detects_a_spliced_chain() -> None:
    """Two internally consistent chains joined together must not verify.

    Every link here reconciles with its own recorded predecessor hash, so the payload
    and sequence checks both pass. Only the link-to-predecessor check catches it. This
    is the splice attack: take a real prefix, graft a different history onto it.
    """
    original = build_chain(2)
    forged = build_chain(2)
    spliced = [original[0], forged[1]]
    with pytest.raises(ChainBrokenError, match="broken link at sequence 2"):
        verify(spliced)


def test_the_predecessor_hash_changes_the_digest() -> None:
    """Without this, deleting the chaining step from chain_hash passes every other test.

    The digest must depend on the predecessor's hash, or `event_hash` is merely a per-event
    checksum and altering an event no longer invalidates everything after it.
    """
    subject = event(1)
    assert chain_hash(subject, GENESIS_HASH) != chain_hash(subject, "f" * 64)


def test_append_rejects_a_non_consecutive_sequence() -> None:
    chain = build_chain(1)
    with pytest.raises(ChainBrokenError, match="expected sequence 2"):
        append(chain, event(5))
