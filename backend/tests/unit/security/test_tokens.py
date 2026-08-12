from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.security.tokens import InvalidTokenError, JwtTokenService

SECRET = "test-secret-not-used-anywhere-real"
SUBJECT = UserId(uuid4())


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


def make_service(clock: FrozenClock) -> JwtTokenService:
    return JwtTokenService(
        secret=SECRET, clock=clock, access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=7)
    )


def test_an_access_token_round_trips_to_its_subject() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    assert service.read_access(service.issue_access(SUBJECT)) == SUBJECT


def test_an_expired_access_token_is_refused() -> None:
    clock = FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC))
    token = make_service(clock).issue_access(SUBJECT)
    clock.moment += timedelta(minutes=16)
    with pytest.raises(InvalidTokenError, match="expired"):
        make_service(clock).read_access(token)


def test_a_token_signed_with_another_secret_is_refused() -> None:
    clock = FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC))
    token = make_service(clock).issue_access(SUBJECT)
    other = JwtTokenService(
        secret="a-different-secret",
        clock=clock,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )
    with pytest.raises(InvalidTokenError):
        other.read_access(token)


def test_a_tampered_token_is_refused() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    token = service.issue_access(SUBJECT)
    with pytest.raises(InvalidTokenError):
        service.read_access(token[:-2] + ("aa" if not token.endswith("aa") else "bb"))


def test_rubbish_is_refused_rather_than_crashing() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    with pytest.raises(InvalidTokenError):
        service.read_access("not.a.token")


def test_an_access_token_cannot_be_used_as_a_refresh_token() -> None:
    """Token confusion: a short-lived credential must not unlock a long-lived one.

    A refresh token is opaque, not a JWT, so `jwt.decode` rejects it for being
    structurally malformed before the `typ` claim is ever inspected — the message is
    therefore "token is not valid", not "wrong token type". (The plan text asserted
    `match="wrong token type"` here; that regex can never match this code path, so it
    was corrected. See the report for the full account: this test cannot exercise the
    `typ` check at all for an opaque refresh token, and does not fail if that check is
    removed.)
    """
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    access = service.issue_access(SUBJECT)
    refresh, _ = service.issue_refresh(SUBJECT, uuid4())
    assert access != refresh
    with pytest.raises(InvalidTokenError):
        service.read_access(refresh)


def test_a_refresh_token_is_stored_only_as_a_hash() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    token, token_hash = service.issue_refresh(SUBJECT, uuid4())
    assert token_hash != token
    assert len(token_hash) == 64
    assert service.hash_refresh(token) == token_hash


def test_two_refresh_tokens_are_never_equal() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    family = uuid4()
    first, _ = service.issue_refresh(SUBJECT, family)
    second, _ = service.issue_refresh(SUBJECT, family)
    assert first != second
