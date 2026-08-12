"""Universal invariants, asserted over generated inputs rather than chosen examples."""

import dataclasses
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from ugjcs.domain.blinding import blind
from ugjcs.domain.enums import EventType
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.events import EditorialEvent, PayloadValue
from ugjcs.domain.hashchain import ChainBrokenError, ChainedEvent, append, verify
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.domain.transitions import LEGAL_TRANSITIONS, TERMINAL_STATES, is_legal

BASE_TIME = datetime(2026, 8, 12, tzinfo=UTC)

payloads = st.dictionaries(
    st.text(min_size=1, max_size=12),
    st.one_of(st.integers(), st.text(max_size=20), st.booleans()),
    max_size=5,
)


def build_chain(payload_list: list[dict[str, PayloadValue]]) -> list[ChainedEvent]:
    """Link a run of events into a chain, one per supplied payload."""
    manuscript_id = ManuscriptId(uuid4())
    actor_id = UserId(uuid4())
    chain: list[ChainedEvent] = []
    for index, payload in enumerate(payload_list, start=1):
        chain.append(
            append(
                chain,
                EditorialEvent(
                    manuscript_id=manuscript_id,
                    sequence=index,
                    event_type=EventType.DECISION_RECORDED,
                    payload=payload,
                    actor_id=actor_id,
                    occurred_at=BASE_TIME + timedelta(minutes=index),
                ),
            )
        )
    return chain


@given(source=st.sampled_from(list(S)), target=st.sampled_from(list(S)))
def test_no_transition_ever_leaves_a_terminal_state(source: S, target: S) -> None:
    if source in TERMINAL_STATES:
        assert not is_legal(source, target)


@given(source=st.sampled_from(list(S)))
def test_published_is_reachable_only_from_scheduled(source: S) -> None:
    if is_legal(source, S.PUBLISHED):
        assert source is S.SCHEDULED


@given(source=st.sampled_from(list(S)))
def test_scheduling_is_reachable_only_from_accepted(source: S) -> None:
    """With the previous property, this makes acceptance a precondition of publication.

    Publication is reachable only from SCHEDULED, and SCHEDULED only from ACCEPTED, so no
    path through the lifetime of a manuscript reaches PUBLISHED without an acceptance.
    """
    if is_legal(source, S.SCHEDULED):
        assert source is S.ACCEPTED


@given(source=st.sampled_from(list(S)))
def test_accepted_is_reachable_only_from_reviews_complete(source: S) -> None:
    if is_legal(source, S.ACCEPTED):
        assert source is S.REVIEWS_COMPLETE


def test_withdrawal_is_reachable_from_every_non_terminal_state_except_draft() -> None:
    expected = {
        state
        for state in S
        if state not in TERMINAL_STATES
        and state not in {S.DRAFT, S.RESUBMITTED, S.ACCEPTED, S.SCHEDULED}
    }
    actual = {state for state in S if S.WITHDRAWN in LEGAL_TRANSITIONS[state]}
    assert actual == expected


@settings(max_examples=100)
@given(payload_list=st.lists(payloads, min_size=1, max_size=12))
def test_a_chain_built_by_append_always_verifies(
    payload_list: list[dict[str, PayloadValue]],
) -> None:
    verify(build_chain(payload_list))


@settings(max_examples=50)
@given(
    payload_list=st.lists(payloads, min_size=2, max_size=8),
    victim=st.integers(min_value=0),
)
def test_removing_any_event_except_the_last_breaks_the_chain(
    payload_list: list[dict[str, PayloadValue]], victim: int
) -> None:
    """The tail is deliberately excluded, because truncation is undetectable by design.

    Any prefix of a valid chain is itself a valid chain, so removing the last event leaves
    nothing inconsistent to find. That limitation is stated in `hashchain`'s module
    docstring and recorded in the technical debt register; closing it needs an external
    anchor. Every other removal must break verification.
    """
    chain = build_chain(payload_list)
    del chain[victim % (len(chain) - 1)]
    try:
        verify(chain)
    except ChainBrokenError:
        return
    raise AssertionError("removing a non-terminal event should always break verification")


@settings(max_examples=100)
@given(payload_list=st.lists(payloads, min_size=1, max_size=6))
def test_truncating_the_tail_is_not_detected(
    payload_list: list[dict[str, PayloadValue]],
) -> None:
    """Pins the known limitation so it cannot change silently.

    If a future change makes truncation detectable, this test fails and forces the
    docstring, the specification and the debt register to be updated together.
    """
    verify(build_chain(payload_list)[:-1])


@given(
    title=st.text(max_size=40),
    abstract=st.text(max_size=80),
    keywords=st.lists(st.text(min_size=1, max_size=15), max_size=4),
)
def test_the_blinded_projection_never_carries_author_identity(
    title: str, abstract: str, keywords: list[str]
) -> None:
    """No manuscript content, however chosen, causes the author id to reach a reviewer."""
    author = UserId(uuid4())
    manuscript = Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 1),
        title=title,
        abstract=abstract,
        keywords=tuple(keywords),
        author_ids=(author,),
        corresponding_author_id=author,
    )
    serialised = repr(dataclasses.asdict(blind(manuscript)))
    assert str(author) not in serialised
