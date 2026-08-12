from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ugjcs.domain.account import Account, AccountError, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_account(**overrides: object) -> Account:
    defaults: dict[str, object] = {
        "id": UserId(uuid4()),
        "email": EmailAddress("R.Obeng@ug.edu.gh"),
        "password_hash": "argon2-placeholder",
        "full_name": "Roger Koranteng Obeng",
        "affiliation": "University of Ghana",
    }
    return Account(**(defaults | overrides))  # type: ignore[arg-type]


def test_email_is_normalised_to_lowercase() -> None:
    assert EmailAddress("R.Obeng@UG.edu.GH").value == "r.obeng@ug.edu.gh"


def test_email_is_stripped_of_surrounding_whitespace() -> None:
    assert EmailAddress("  clerk@ug.edu.gh \n").value == "clerk@ug.edu.gh"


@pytest.mark.parametrize("raw", ["", "not-an-email", "a@", "@b.com", "a b@c.com"])
def test_malformed_email_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="not a valid email address"):
        EmailAddress(raw)


def test_a_new_account_is_unverified_and_active() -> None:
    account = make_account()
    assert not account.is_verified
    assert account.is_active


def test_a_new_account_holds_no_roles() -> None:
    assert make_account().roles == frozenset()


def test_verification_marks_the_account_verified() -> None:
    account = make_account()
    account.verify(occurred_at=NOW)
    assert account.is_verified
    assert account.verified_at == NOW


def test_verifying_twice_is_refused() -> None:
    account = make_account()
    account.verify(occurred_at=NOW)
    with pytest.raises(AccountError, match="already verified"):
        account.verify(occurred_at=NOW)


def test_roles_can_be_granted_and_revoked() -> None:
    account = make_account()
    account.grant(Role.REVIEWER)
    account.grant(Role.EDITOR)
    assert account.roles == frozenset({Role.REVIEWER, Role.EDITOR})
    account.revoke(Role.EDITOR)
    assert account.roles == frozenset({Role.REVIEWER})


def test_granting_a_held_role_is_idempotent() -> None:
    account = make_account()
    account.grant(Role.AUTHOR)
    account.grant(Role.AUTHOR)
    assert account.roles == frozenset({Role.AUTHOR})


def test_revoking_a_role_not_held_is_refused() -> None:
    account = make_account()
    with pytest.raises(AccountError, match="does not hold"):
        account.revoke(Role.EDITOR)


def test_a_deactivated_account_may_not_authenticate() -> None:
    account = make_account()
    account.verify(occurred_at=NOW)
    account.deactivate()
    assert not account.is_active
    assert not account.may_authenticate()


def test_an_unverified_account_may_not_authenticate() -> None:
    assert not make_account().may_authenticate()


def test_a_verified_active_account_may_authenticate() -> None:
    account = make_account()
    account.verify(occurred_at=NOW)
    assert account.may_authenticate()
