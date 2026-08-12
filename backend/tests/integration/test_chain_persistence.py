"""The chain must verify after a round trip, and keep verifying as events accumulate."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.enums import DecisionType
from ugjcs.domain.hashchain import GENESIS_HASH, verify
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.db.repository import SqlAlchemyManuscriptRepository

pytestmark = pytest.mark.integration

AUTHOR = UserId(uuid4())
EDITOR = UserId(uuid4())
NOW = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)


def make_manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 33),
        title="Fair Scheduling for Shared GPU Clusters",
        abstract="A scheduler balancing fairness against utilisation.",
        keywords=("scheduling",),
        author_ids=(AUTHOR,),
        corresponding_author_id=AUTHOR,
    )


async def test_a_persisted_chain_verifies(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    verify(chain)
    assert len(chain) == 1
    assert chain[0].previous_hash == GENESIS_HASH


async def test_the_chain_stays_consecutive_across_separate_transactions(
    session: AsyncSession,
) -> None:
    """The regression this whole plan exists to prevent.

    Each save drains the aggregate's buffer. If rehydration failed to restore the sequence
    counter, the second transaction would emit sequence 1 again and `append` would reject it.
    """
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    reloaded = await repository.get(manuscript.id)
    assert reloaded is not None
    reloaded.record_decision(
        decision=DecisionType.SEND_TO_REVIEW,
        actor_id=EDITOR,
        rationale="In scope",
        occurred_at=NOW,
    )
    await repository.save(reloaded)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    verify(chain)
    assert [link.event.sequence for link in chain] == [1, 2, 3]


async def test_each_stored_link_points_at_its_predecessor(session: AsyncSession) -> None:
    repository = SqlAlchemyManuscriptRepository(session)
    manuscript = make_manuscript()
    manuscript.submit(actor_id=AUTHOR, occurred_at=NOW)
    await repository.add(manuscript)
    await session.commit()

    loaded = await repository.get(manuscript.id)
    assert loaded is not None
    loaded.begin_screening(actor_id=EDITOR, occurred_at=NOW)
    await repository.save(loaded)
    await session.commit()

    chain = await repository.chain_for(manuscript.id)
    assert chain[1].previous_hash == chain[0].event_hash
