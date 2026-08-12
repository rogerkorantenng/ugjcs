import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.enums import EventType
from ugjcs.domain.events import EditorialEvent
from ugjcs.domain.ids import ManuscriptId, UserId

# Identity is pinned at module level: canonical_bytes() covers the identity fields as
# well as the payload, so a fixture that minted fresh UUIDs per call would make every
# event differ regardless of payload key order, and the determinism test would be vacuous.
MANUSCRIPT = ManuscriptId(uuid4())
ACTOR = UserId(uuid4())


def make_event(**overrides: object) -> EditorialEvent:
    defaults: dict[str, object] = {
        "manuscript_id": MANUSCRIPT,
        "sequence": 1,
        "event_type": EventType.MANUSCRIPT_SUBMITTED,
        "payload": {"title": "On Kente Pattern Recognition"},
        "actor_id": ACTOR,
        "occurred_at": datetime(2026, 8, 12, 9, 30, tzinfo=UTC),
    }
    return EditorialEvent(**(defaults | overrides))  # type: ignore[arg-type]


def test_event_is_immutable() -> None:
    event = make_event()
    with pytest.raises(AttributeError):
        event.sequence = 2  # type: ignore[misc]


def test_sequence_must_be_positive() -> None:
    with pytest.raises(ValueError, match="sequence must be positive"):
        make_event(sequence=0)


def test_occurred_at_must_be_timezone_aware() -> None:
    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        make_event(occurred_at=datetime(2026, 8, 12, 9, 30))


def test_canonical_bytes_are_stable_across_key_order() -> None:
    a = make_event(payload={"alpha": 1, "beta": 2})
    b = make_event(payload={"beta": 2, "alpha": 1})
    assert a.canonical_bytes() == b.canonical_bytes()


def test_canonical_bytes_change_when_payload_changes() -> None:
    a = make_event(payload={"alpha": 1})
    b = make_event(payload={"alpha": 2})
    assert a.canonical_bytes() != b.canonical_bytes()


def test_canonical_bytes_refuses_a_value_it_cannot_serialise_stably() -> None:
    """A set's str() follows iteration order, which varies with the process hash seed.

    Serialising it would produce different bytes for the same event in a different
    process, so the chain would report tampering that never happened. Refusing loudly
    is the only safe behaviour.
    """
    event = make_event(payload={"tags": {"a", "b"}})
    with pytest.raises(TypeError):
        event.canonical_bytes()


def test_canonical_bytes_refuses_a_non_finite_float() -> None:
    """json.dumps would emit bare NaN, which is not valid JSON and no jsonb column accepts."""
    event = make_event(payload={"score": float("nan")})
    with pytest.raises(ValueError):
        event.canonical_bytes()


def test_canonical_bytes_are_valid_json() -> None:
    event = make_event(payload={"score": 4.5, "note": "ok", "flag": True, "absent": None})
    assert json.loads(event.canonical_bytes())["payload"]["score"] == 4.5


def test_a_system_event_has_no_actor() -> None:
    """Some events originate from the system, not a person; the serialiser must handle it."""
    event = make_event(actor_id=None)
    assert json.loads(event.canonical_bytes())["actor_id"] is None
