# UGJCS Plan 3 — Authentication and Identity

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish who a request is from, and assemble the `Actor` the authorisation layer already consumes — with roles that are current rather than merely authentic.

**Architecture:** Password hashing and token issuance are ports in `application/ports.py` with adapters in `infrastructure/security/`. The access token carries only a subject identifier; roles are read from the database on every request. Refresh tokens rotate on use, are stored only as hashes, and are grouped into families so that replaying a spent token revokes the whole family.

**Tech Stack:** argon2-cffi, PyJWT, SQLAlchemy 2.0 async, Alembic, pytest-asyncio, testcontainers.

## Global Constraints

- Python **3.13**, all tooling via `uv run` from `backend/`.
- The layered import contract from Plan 2 holds: `domain` may not import `application` or `infrastructure`; `application` may not import `infrastructure`. The domain still imports no framework.
- Timestamps are timezone-aware UTC; every `DateTime` column is `timezone=True`.
- Coverage gate stays at **85%**; `make check` green at every commit. Integration tests are marked `@pytest.mark.integration` and deselected by default.
- mypy `strict`; ruff line-length 100, select `["E","F","I","N","UP","B","A","C4","SIM","RUF"]`.
- **`ruff format` is authoritative** over hand-written line breaks. Any other lint failure is escalated, never suppressed: no `# noqa`, `# fmt: off`, `# pragma: no cover`, or `pyproject.toml` edits. The sole exceptions are registration-side-effect imports in Alembic `env.py` and test conftest, already authorised in Plan 2.
- A project-wide 100-line file-size hook may fire. **It is not a gate.** Ignore it without justification.
- **No secret may have a default value.** A missing `UGJCS_JWT_SECRET` must fail at startup, loudly. A development fallback is how production ends up signing tokens with a value published on GitHub.
- **Never log a password, a token, or a token hash** — not at debug level, not in an exception message.
- Conventional Commits. Author: Roger Koranteng Obeng, student ID 22424140.

## Interfaces inherited from Plans 1 and 2

- `ugjcs.domain.enums.Role` — `AUTHOR`, `REVIEWER`, `EDITOR`, `EDITOR_IN_CHIEF`, `ADMINISTRATOR`
- `ugjcs.domain.policies` — `Actor(id: UserId, roles: frozenset[Role])`, `Action`, `can(...)`, `authorize(...)`
- `ugjcs.domain.ids.UserId` — `NewType` over `UUID`
- `ugjcs.domain.errors.DomainError` and its subclasses
- `ugjcs.application.ports` — `ManuscriptRepository`, `UnitOfWork` protocols
- `ugjcs.infrastructure.db` — `Base`, `create_engine`, `session_factory`, `SqlAlchemyUnitOfWork`
- Alembic revision `0001` is the current head; this plan adds `0002`.

## The finding this plan answers

Plan 1's Task 8 review recorded: *"`Actor.roles` is caller-supplied and unverified by this layer. The JWT/session layer must guarantee roles are authentic and CURRENT (not stale) before constructing an `Actor`."*

Encoding roles as token claims satisfies "authentic" and fails "current": an administrator who revokes an editor's role would not take effect until that editor's token expired, leaving a demoted user with editorial powers for the remainder of the token's life. Task 6 therefore reads roles from the database per request and proves revocation is immediate.

---

## File Structure

```
backend/
├── src/ugjcs/
│   ├── domain/
│   │   └── account.py                           Task 1  Account aggregate, credential rules
│   ├── application/
│   │   ├── ports.py                             Task 1  hasher, tokens, clock, email
│   │   │                                         (extended Task 5: AccountRepository, UnitOfWork.accounts)
│   │   │                                         (extended Task 7: TokenService.issue/read_verification)
│   │   │                                         (extended Task 8: RefreshTokenRecord/Repository,
│   │   │                                          UnitOfWork.refresh_tokens, TokenService.refresh_ttl)
│   │   └── identity.py                          Task 6  IdentityService.actor_for, AuthenticationError
│   │                                             (extended Task 7: RegistrationService)
│   │                                             (extended Task 8: SessionService, TokenPair)
│   └── infrastructure/
│       ├── security/
│       │   ├── __init__.py                      Task 3
│       │   ├── passwords.py                     Task 3  Argon2id adapter
│       │   └── tokens.py                        Task 4  JWT access + rotating refresh
│       │                                         (extended Task 7: issue_verification/read_verification)
│       ├── email/
│       │   ├── __init__.py                      Task 7
│       │   └── logging_sender.py                Task 7  writes the link to the log
│       └── db/
│           ├── models.py                        Task 2  (extended) users, user_roles, refresh_tokens
│           ├── mappers.py                       Task 2  event/manuscript mapping
│           │                                     (extended Task 5: account_to_row/row_to_account)
│           │                                     (extended Task 8: refresh token mapping)
│           ├── uow.py                            Task 2  SqlAlchemyUnitOfWork
│           │                                     (extended Task 5: .accounts, Task 8: .refresh_tokens)
│           ├── account_repository.py            Task 5
│           └── refresh_token_repository.py      Task 8
├── alembic/versions/0002_identity.py            Task 2
└── tests/
    ├── unit/domain/test_account.py              Task 1
    ├── unit/security/test_passwords.py          Task 3
    ├── unit/security/test_tokens.py             Task 4
    ├── unit/application/test_identity.py        Task 7
    └── integration/
        ├── test_account_repository.py           Task 5
        ├── test_actor_assembly.py               Task 6
        └── test_refresh_rotation.py             Task 8
```

---

### Task 1: Account aggregate and the security ports

**Files:**
- Create: `backend/src/ugjcs/domain/account.py`, `backend/tests/unit/domain/test_account.py`
- Modify: `backend/src/ugjcs/application/ports.py`

**Interfaces:**
- Produces: `EmailAddress`, `Account`, `AccountError`; and the `PasswordHasher`, `TokenService`, `Clock`, `EmailSender` protocols.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_account.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/domain/test_account.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.domain.account'`

**A caution before you write it.** `EmailAddress` is a frozen `slots=True` dataclass with a
hand-written `__init__` that normalises before validating. This works — `dataclasses` does not
overwrite an `__init__` already present in the class body — but it is unusual enough that mypy or
the dataclass machinery may object under this project's settings. If either does, report the exact
error rather than restructuring: switching to `__post_init__` would validate *after* the frozen
instance is built and require `object.__setattr__` anyway, and a `classmethod` factory would let
callers bypass normalisation entirely by calling the constructor directly.

- [ ] **Step 3: Write the aggregate**

Create `backend/src/ugjcs/domain/account.py`:

```python
"""The account aggregate: who someone is, and what they are allowed to be.

The password *hash* lives here; hashing itself does not. Choosing an algorithm is an
infrastructure concern, and keeping it out preserves the domain's freedom from libraries.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from ugjcs.domain.enums import Role
from ugjcs.domain.errors import DomainError
from ugjcs.domain.ids import UserId

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")


class AccountError(DomainError):
    """An operation the account's current state does not permit."""


@dataclass(frozen=True, slots=True)
class EmailAddress:
    """A normalised address. Case and surrounding whitespace never distinguish accounts."""

    value: str

    def __init__(self, raw: str) -> None:
        normalised = raw.strip().lower()
        if not _EMAIL_PATTERN.match(normalised):
            raise ValueError(f"not a valid email address: {raw!r}")
        object.__setattr__(self, "value", normalised)


@dataclass(slots=True)
class Account:
    id: UserId
    email: EmailAddress
    password_hash: str
    full_name: str
    affiliation: str
    expertise: tuple[str, ...] = ()
    reviewer_capacity: int = 3
    is_verified: bool = False
    is_active: bool = True
    verified_at: datetime | None = None
    _roles: set[Role] = field(default_factory=set, repr=False)

    @property
    def roles(self) -> frozenset[Role]:
        return frozenset(self._roles)

    def verify(self, *, occurred_at: datetime) -> None:
        if self.is_verified:
            raise AccountError("account is already verified")
        self.is_verified = True
        self.verified_at = occurred_at

    def grant(self, role: Role) -> None:
        """Idempotent: granting a held role is a no-op, not an error."""
        self._roles.add(role)

    def revoke(self, role: Role) -> None:
        if role not in self._roles:
            raise AccountError(f"account does not hold the {role.value} role")
        self._roles.discard(role)

    def deactivate(self) -> None:
        self.is_active = False

    def reactivate(self) -> None:
        self.is_active = True

    def may_authenticate(self) -> bool:
        """Both conditions are required; neither implies the other."""
        return self.is_verified and self.is_active
```

- [ ] **Step 4: Extend the ports**

Append to `backend/src/ugjcs/application/ports.py`:

```python
class Clock(Protocol):
    """Time as a dependency, so expiry logic is testable without sleeping."""

    def now(self) -> datetime: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Constant-time where the algorithm allows. Returns False; never raises on mismatch."""
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """True when the hash was produced with weaker parameters than current policy."""
        ...


class TokenService(Protocol):
    def issue_access(self, subject: UserId) -> str: ...

    def read_access(self, token: str) -> UserId:
        """Return the subject, or raise `InvalidTokenError` if absent, expired or tampered with."""
        ...

    def issue_refresh(self, subject: UserId, family_id: UUID) -> tuple[str, str]:
        """Return `(token, token_hash)`. Only the hash is ever stored."""
        ...

    def hash_refresh(self, token: str) -> str: ...


class EmailSender(Protocol):
    async def send_verification(self, to: str, link: str) -> None: ...
```

Extend that module's imports with `from datetime import datetime`, `from uuid import UUID`, and `from ugjcs.domain.ids import UserId`.

- [ ] **Step 5: Run the tests, then the gates**

Run: `cd backend && uv run pytest tests/unit/domain/test_account.py -v` — expect the tests to pass; report the actual count.
Run: `cd backend && make check` — all gates green, both import contracts KEPT.

- [ ] **Step 6: Commit**

```bash
git add backend/src/ugjcs/domain/account.py backend/src/ugjcs/application/ports.py backend/tests/unit/domain/test_account.py
git commit -m "feat: add the account aggregate and security ports"
```

---

### Task 2: Identity schema

**Files:**
- Modify: `backend/src/ugjcs/infrastructure/db/models.py`
- Create: `backend/alembic/versions/0002_identity.py`

**Interfaces:**
- Produces: `UserRow`, `UserRoleRow`, `RefreshTokenRow`; migration `0002`.

- [ ] **Step 1: Add the models**

Append to `backend/src/ugjcs/infrastructure/db/models.py`:

```python
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    affiliation: Mapped[str] = mapped_column(String(255))
    expertise: Mapped[list[str]] = mapped_column(postgresql.ARRAY(Text), default=list)
    reviewer_capacity: Mapped[int] = mapped_column(Integer, default=3)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    roles: Mapped[list["UserRoleRow"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (CheckConstraint("reviewer_capacity >= 0", name="capacity_non_negative"),)


class UserRoleRow(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(32), primary_key=True)

    user: Mapped[UserRow] = relationship(back_populates="roles")


class RefreshTokenRow(Base):
    """Only hashes are stored. A stolen database yields no usable refresh token."""

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        postgresql.UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[UUID] = mapped_column(postgresql.UUID(as_uuid=True), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by: Mapped[UUID | None] = mapped_column(postgresql.UUID(as_uuid=True), nullable=True)
```

Extend that module's imports with `Boolean` from `sqlalchemy`.

- [ ] **Step 2: Write migration 0002**

Create `backend/alembic/versions/0002_identity.py` creating `users`, `user_roles` and `refresh_tokens` with the columns, constraints and indexes above. Follow revision `0001`'s style exactly: explicit constraint names matching the naming convention, `postgresql.UUID(as_uuid=True)`, `sa.DateTime(timezone=True)`, and a `downgrade()` that drops the three tables in reverse dependency order (`refresh_tokens`, `user_roles`, `users`).

Set `revision = "0002"` and `down_revision = "0001"`.

- [ ] **Step 3: Verify the migration round-trips**

```bash
docker run --rm -d --name ugjcs-mig2 -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=ugjcs -p 55433:5432 postgres:16
sleep 5
cd backend
export UGJCS_DATABASE_URL=postgresql+asyncpg://postgres:pw@localhost:55433/ugjcs
uv run alembic upgrade head
uv run alembic downgrade 0001
uv run alembic upgrade head
docker rm -f ugjcs-mig2
```
Expected: all succeed. Confirm `alembic downgrade 0001` leaves the Plan 2 tables intact.

- [ ] **Step 4: Run the gates and commit**

```bash
git add backend/src/ugjcs/infrastructure/db/models.py backend/alembic/versions/0002_identity.py
git commit -m "feat: add identity schema for users, roles and refresh tokens"
```

---

### Task 3: Argon2id password hashing

**Files:**
- Create: `backend/src/ugjcs/infrastructure/security/__init__.py`, `backend/src/ugjcs/infrastructure/security/passwords.py`, `backend/tests/unit/security/__init__.py`, `backend/tests/unit/security/test_passwords.py`

**Interfaces:**
- Produces: `Argon2PasswordHasher` implementing the `PasswordHasher` port.

- [ ] **Step 1: Add the dependency**

```bash
cd backend && uv add argon2-cffi
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/security/__init__.py` (empty) and `backend/tests/unit/security/test_passwords.py`:

```python
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher

PASSWORD = "correct horse battery staple"


def test_a_hash_is_not_the_password() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.hash(PASSWORD) != PASSWORD


def test_hashing_is_salted_so_two_hashes_differ() -> None:
    """Equal passwords must not produce equal hashes, or the database leaks which users share one."""
    hasher = Argon2PasswordHasher()
    assert hasher.hash(PASSWORD) != hasher.hash(PASSWORD)


def test_a_correct_password_verifies() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.verify(PASSWORD, hasher.hash(PASSWORD))


def test_an_incorrect_password_does_not_verify() -> None:
    hasher = Argon2PasswordHasher()
    assert not hasher.verify("wrong password", hasher.hash(PASSWORD))


def test_verification_returns_false_rather_than_raising_on_a_malformed_hash() -> None:
    """A corrupt stored hash must fail closed, not crash the login endpoint."""
    hasher = Argon2PasswordHasher()
    assert not hasher.verify(PASSWORD, "not-a-real-argon2-hash")


def test_the_hash_identifies_argon2id() -> None:
    assert Argon2PasswordHasher().hash(PASSWORD).startswith("$argon2id$")


def test_a_current_hash_does_not_need_rehashing() -> None:
    hasher = Argon2PasswordHasher()
    assert not hasher.needs_rehash(hasher.hash(PASSWORD))


def test_a_weaker_hash_needs_rehashing() -> None:
    """Raising cost parameters later must be detectable on the next successful login."""
    weak = Argon2PasswordHasher(memory_cost=8, time_cost=1, parallelism=1)
    assert Argon2PasswordHasher().needs_rehash(weak.hash(PASSWORD))
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd backend && uv run pytest tests/unit/security/test_passwords.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Write the adapter**

Create `backend/src/ugjcs/infrastructure/security/passwords.py`:

```python
"""Argon2id password hashing.

Parameters follow the OWASP Password Storage Cheat Sheet's Argon2id recommendation:
19 MiB of memory, two iterations, one degree of parallelism. Memory hardness is what
makes GPU-parallel cracking expensive, so `memory_cost` is the value to raise first if
these are ever revisited.
"""

from argon2 import PasswordHasher as Argon2
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

DEFAULT_MEMORY_COST = 19456
DEFAULT_TIME_COST = 2
DEFAULT_PARALLELISM = 1


class Argon2PasswordHasher:
    def __init__(
        self,
        *,
        memory_cost: int = DEFAULT_MEMORY_COST,
        time_cost: int = DEFAULT_TIME_COST,
        parallelism: int = DEFAULT_PARALLELISM,
    ) -> None:
        self._hasher = Argon2(
            memory_cost=memory_cost, time_cost=time_cost, parallelism=parallelism
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        """False on any failure. A corrupt stored hash must not crash the login path."""
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError:
            return True
```

- [ ] **Step 5: Run the tests, gates, and commit**

Run the module's tests, report the count, then `make check`.

```bash
git add backend/src/ugjcs/infrastructure/security backend/tests/unit/security backend/pyproject.toml backend/uv.lock
git commit -m "feat: add Argon2id password hashing at OWASP-recommended parameters"
```

---

### Task 4: Tokens

**Files:**
- Create: `backend/src/ugjcs/infrastructure/security/tokens.py`, `backend/tests/unit/security/test_tokens.py`
- Modify: `backend/src/ugjcs/infrastructure/config.py`

**Interfaces:**
- Produces: `InvalidTokenError`, `JwtTokenService(secret, clock, access_ttl, refresh_ttl)`, `SystemClock`.

- [ ] **Step 1: Add the dependency and settings**

```bash
cd backend && uv add pyjwt
```

Add to `Settings` in `config.py`:

```python
    jwt_secret: str = Field(description="HMAC signing key; no default, must be supplied")
    access_token_minutes: int = Field(default=15, description="Access token lifetime")
    refresh_token_days: int = Field(default=7, description="Refresh token lifetime")
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/security/test_tokens.py`:

```python
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
    return JwtTokenService(secret=SECRET, clock=clock, access_ttl=timedelta(minutes=15),
                           refresh_ttl=timedelta(days=7))


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
    other = JwtTokenService(secret="a-different-secret", clock=clock,
                            access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=7))
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
    """Token confusion: a short-lived credential must not unlock a long-lived one."""
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    access = service.issue_access(SUBJECT)
    refresh, _ = service.issue_refresh(SUBJECT, uuid4())
    assert access != refresh
    with pytest.raises(InvalidTokenError, match="wrong token type"):
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
```

- [ ] **Step 3: Run to verify it fails, then write the adapter**

Create `backend/src/ugjcs/infrastructure/security/tokens.py`:

```python
"""Access and refresh tokens.

The access token carries the subject and nothing else — deliberately no roles. A role
encoded as a claim is a snapshot: revoking it would not take effect until the token
expired, leaving a demoted user with powers they no longer hold. Roles are read from the
database per request instead, which costs one indexed query and makes revocation immediate.

Refresh tokens are opaque random strings, never JWTs, and only their SHA-256 hashes are
stored. A stolen database therefore yields nothing a thief can present.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from ugjcs.application.ports import Clock
from ugjcs.domain.errors import DomainError
from ugjcs.domain.ids import UserId

ALGORITHM = "HS256"
ACCESS_TYPE = "access"


class InvalidTokenError(DomainError):
    """A token that is absent, malformed, expired, of the wrong type, or not ours."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class JwtTokenService:
    def __init__(
        self, *, secret: str, clock: Clock, access_ttl: timedelta, refresh_ttl: timedelta
    ) -> None:
        self._secret = secret
        self._clock = clock
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl

    def issue_access(self, subject: UserId) -> str:
        issued = self._clock.now()
        return jwt.encode(
            {
                "sub": str(subject),
                "typ": ACCESS_TYPE,
                "iat": int(issued.timestamp()),
                "exp": int((issued + self._access_ttl).timestamp()),
            },
            self._secret,
            algorithm=ALGORITHM,
        )

    def read_access(self, token: str) -> UserId:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError as error:
            raise InvalidTokenError("token has expired") from error
        except jwt.PyJWTError as error:
            raise InvalidTokenError("token is not valid") from error
        if claims.get("typ") != ACCESS_TYPE:
            raise InvalidTokenError("wrong token type for this endpoint")
        try:
            return UserId(UUID(claims["sub"]))
        except (KeyError, ValueError) as error:
            raise InvalidTokenError("token subject is missing or malformed") from error

    def issue_refresh(self, subject: UserId, family_id: UUID) -> tuple[str, str]:
        """Opaque and unguessable. The subject and family are recorded in the database row."""
        token = secrets.token_urlsafe(48)
        return token, self.hash_refresh(token)

    def hash_refresh(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @property
    def refresh_ttl(self) -> timedelta:
        return self._refresh_ttl
```

Note `read_access` decodes a *refresh* token as rubbish — a refresh token is not a JWT, so `jwt.decode` raises and the `typ` check is belt-and-braces for any future JWT-shaped token. Confirm `test_an_access_token_cannot_be_used_as_a_refresh_token` passes; if it fails on the `match="wrong token type"` assertion, report it rather than loosening the assertion — the failure would mean the two token kinds are more confusable than intended.

- [ ] **Step 4: Run the tests, gates, and commit**

```bash
git add backend/src/ugjcs/infrastructure/security/tokens.py backend/src/ugjcs/infrastructure/config.py backend/tests/unit/security/test_tokens.py backend/pyproject.toml backend/uv.lock
git commit -m "feat: add JWT access tokens and opaque hashed refresh tokens"
```

---

### Task 5: Account repository

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/account_repository.py`, `backend/tests/integration/test_account_repository.py`
- Modify: `backend/src/ugjcs/infrastructure/db/mappers.py`, `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/db/uow.py`

**Interfaces:**
- Produces: `AccountRepository` protocol with `add`, `get`, `get_by_email`, `save`; `SqlAlchemyAccountRepository`; `account_to_row` and `row_to_account` mappers; `UnitOfWork.accounts`.

- [ ] **Step 1: Extend the ports**

Append to `backend/src/ugjcs/application/ports.py`. Add the import `from ugjcs.domain.account import Account, EmailAddress` alongside the existing imports.

```python
class AccountRepository(Protocol):
    """Persistence for the account aggregate and its role grants."""

    async def add(self, account: Account) -> None:
        """Persist an account that has never been stored before."""
        ...

    async def get(self, user_id: UserId) -> Account | None: ...

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        """Look up by the normalised address. Case and whitespace never distinguish accounts."""
        ...

    async def save(self, account: Account) -> None:
        """Persist scalar field changes and replace the role rows to match `account.roles`."""
        ...
```

Add `manuscripts`' sibling to `UnitOfWork`:

```python
class UnitOfWork(Protocol):
    manuscripts: ManuscriptRepository
    accounts: AccountRepository
    ...
```

- [ ] **Step 2: Write the mappers**

Append to `backend/src/ugjcs/infrastructure/db/mappers.py`. Extend its imports with `from ugjcs.domain.account import Account, EmailAddress`, `Role` from `ugjcs.domain.enums` (alongside the existing `EventType` and `ManuscriptStatus as S` import), and `UserRoleRow`, `UserRow` from `ugjcs.infrastructure.db.models`.

```python
def account_to_row(account: Account) -> UserRow:
    """Project the aggregate onto a storage row, roles included."""
    return UserRow(
        id=account.id,
        email=account.email.value,
        password_hash=account.password_hash,
        full_name=account.full_name,
        affiliation=account.affiliation,
        expertise=list(account.expertise),
        reviewer_capacity=account.reviewer_capacity,
        is_verified=account.is_verified,
        is_active=account.is_active,
        verified_at=account.verified_at,
        roles=[UserRoleRow(user_id=account.id, role=role.value) for role in account.roles],
    )


def row_to_account(row: UserRow) -> Account:
    """Rebuild the aggregate, restoring roles through the private attribute.

    A public `roles` setter would let any caller rewrite the role set directly, bypassing
    `grant`/`revoke` and the invariants they enforce — the same reasoning `to_domain`
    already applies to `Manuscript._sequence`.
    """
    account = Account(
        id=UserId(row.id),
        email=EmailAddress(row.email),
        password_hash=row.password_hash,
        full_name=row.full_name,
        affiliation=row.affiliation,
        expertise=tuple(row.expertise),
        reviewer_capacity=row.reviewer_capacity,
        is_verified=row.is_verified,
        is_active=row.is_active,
        verified_at=row.verified_at,
    )
    account._roles = {Role(role_row.role) for role_row in row.roles}
    return account
```

- [ ] **Step 3: Write the failing integration test**

Create `backend/tests/integration/test_account_repository.py`:

```python
"""Integration tests for account persistence."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


def make_account(**overrides: object) -> Account:
    defaults: dict[str, object] = {
        "id": UserId(uuid4()),
        "email": EmailAddress("R.Obeng@UG.edu.gh"),
        "password_hash": "argon2-placeholder",
        "full_name": "Roger Koranteng Obeng",
        "affiliation": "University of Ghana",
    }
    return Account(**(defaults | overrides))  # type: ignore[arg-type]


async def test_a_stored_account_reads_back_with_its_roles(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    account.grant(Role.REVIEWER)
    account.grant(Role.EDITOR)
    await repository.add(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.id == account.id
    assert loaded.roles == frozenset({Role.REVIEWER, Role.EDITOR})


async def test_lookup_by_email_is_case_insensitive(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account(email=EmailAddress("R.Obeng@UG.edu.gh"))
    await repository.add(account)
    await session.commit()

    loaded = await repository.get_by_email(EmailAddress("r.obeng@ug.edu.gh"))
    assert loaded is not None
    assert loaded.id == account.id


async def test_a_missing_account_reads_back_as_none(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    assert await repository.get(UserId(uuid4())) is None
    assert await repository.get_by_email(EmailAddress("nobody@ug.edu.gh")) is None


async def test_granting_a_role_and_saving_persists_it(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    await repository.add(account)
    await session.commit()

    account.grant(Role.AUTHOR)
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.AUTHOR})


async def test_revoking_a_role_and_saving_removes_it(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    account.grant(Role.AUTHOR)
    account.grant(Role.REVIEWER)
    await repository.add(account)
    await session.commit()

    account.revoke(Role.AUTHOR)
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.roles == frozenset({Role.REVIEWER})


async def test_saving_persists_scalar_field_changes_too(session: AsyncSession) -> None:
    """Roles are not the only thing `save` must persist. An implementation that only
    rewrites the role table and forgets scalar columns would still pass every test above."""
    repository = SqlAlchemyAccountRepository(session)
    account = make_account()
    await repository.add(account)
    await session.commit()

    account.verify(occurred_at=NOW)
    account.deactivate()
    await repository.save(account)
    await session.commit()

    loaded = await repository.get(account.id)
    assert loaded is not None
    assert loaded.is_verified
    assert loaded.verified_at == NOW
    assert not loaded.is_active


async def test_a_duplicate_email_raises_an_integrity_error(session: AsyncSession) -> None:
    repository = SqlAlchemyAccountRepository(session)
    await repository.add(make_account(email=EmailAddress("dup@ug.edu.gh")))
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.add(make_account(id=UserId(uuid4()), email=EmailAddress("DUP@ug.edu.GH")))
        await session.commit()
```

Run: `cd backend && uv run pytest tests/integration/test_account_repository.py -v -m integration`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.infrastructure.db.account_repository'`.

- [ ] **Step 4: Write the repository**

Create `backend/src/ugjcs/infrastructure/db/account_repository.py`:

```python
"""PostgreSQL implementation of the account repository port."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.mappers import account_to_row, row_to_account
from ugjcs.infrastructure.db.models import UserRoleRow, UserRow


class SqlAlchemyAccountRepository:
    """Persists the account aggregate and keeps its role rows in sync."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, account: Account) -> None:
        self._session.add(account_to_row(account))

    async def get(self, user_id: UserId) -> Account | None:
        row = await self._session.get(UserRow, user_id)
        return row_to_account(row) if row is not None else None

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        result = await self._session.execute(select(UserRow).where(UserRow.email == email.value))
        row = result.scalar_one_or_none()
        return row_to_account(row) if row is not None else None

    async def save(self, account: Account) -> None:
        row = await self._session.get(UserRow, account.id)
        if row is None:
            raise LookupError(f"account {account.id} has never been persisted")
        row.email = account.email.value
        row.password_hash = account.password_hash
        row.full_name = account.full_name
        row.affiliation = account.affiliation
        row.expertise = list(account.expertise)
        row.reviewer_capacity = account.reviewer_capacity
        row.is_verified = account.is_verified
        row.is_active = account.is_active
        row.verified_at = account.verified_at
        held = {existing.role for existing in row.roles}
        wanted = {role.value for role in account.roles}
        for existing in list(row.roles):
            if existing.role not in wanted:
                row.roles.remove(existing)
        for role in wanted - held:
            row.roles.append(UserRoleRow(user_id=account.id, role=role))
```

`row.roles.remove(existing)` relies on the relationship's `cascade="all, delete-orphan"` (Task 2) to delete the orphaned `UserRoleRow`; appending a fresh `UserRoleRow` for each newly-granted role mirrors `to_row`'s construction of `ManuscriptAuthorRow`.

- [ ] **Step 5: Wire the unit of work**

Modify `backend/src/ugjcs/infrastructure/db/uow.py`:

```python
class SqlAlchemyUnitOfWork:
    manuscripts: SqlAlchemyManuscriptRepository
    accounts: SqlAlchemyAccountRepository

    ...

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.manuscripts = SqlAlchemyManuscriptRepository(self._session)
        self.accounts = SqlAlchemyAccountRepository(self._session)
        return self
```

Add the import `from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository`.

- [ ] **Step 6: Run the tests, gates, and commit**

Run: `cd backend && uv run pytest tests/integration/test_account_repository.py tests/integration/test_unit_of_work.py -v -m integration` — expect all to pass; report the actual count.
Run: `cd backend && make check` — both import contracts KEPT.

```bash
git add backend/src/ugjcs/infrastructure/db/account_repository.py backend/src/ugjcs/infrastructure/db/mappers.py backend/src/ugjcs/infrastructure/db/uow.py backend/src/ugjcs/application/ports.py backend/tests/integration/test_account_repository.py
git commit -m "feat: persist accounts and their roles"
```

---

### Task 6: Actor assembly — the finding this plan answers

**Files:**
- Create: `backend/src/ugjcs/application/identity.py`, `backend/tests/integration/test_actor_assembly.py`

**Interfaces:**
- Produces: `AuthenticationError`; `IdentityService.actor_for(access_token) -> Actor`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_actor_assembly.py`:

```python
"""Integration tests proving roles are read fresh, not carried by the token.

Discharges Plan 1's Task 8 review finding: `Actor.roles` must be authentic AND current.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.identity import AuthenticationError, IdentityService
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository
from ugjcs.infrastructure.security.tokens import InvalidTokenError, JwtTokenService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


def make_account(**overrides: object) -> Account:
    defaults: dict[str, object] = {
        "id": UserId(uuid4()),
        "email": EmailAddress(f"{uuid4()}@ug.edu.gh"),
        "password_hash": "argon2-placeholder",
        "full_name": "Roger Koranteng Obeng",
        "affiliation": "University of Ghana",
    }
    return Account(**(defaults | overrides))  # type: ignore[arg-type]


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(NOW)


@pytest.fixture
def tokens(clock: FrozenClock) -> JwtTokenService:
    return JwtTokenService(
        secret="test-secret-not-used-anywhere-real",
        clock=clock,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


@pytest.fixture
def repository(session: AsyncSession) -> SqlAlchemyAccountRepository:
    return SqlAlchemyAccountRepository(session)


@pytest.fixture
def identity(repository: SqlAlchemyAccountRepository, tokens: JwtTokenService) -> IdentityService:
    return IdentityService(repository, tokens)


async def verified_account_with(
    session: AsyncSession, repository: SqlAlchemyAccountRepository, *roles: Role
) -> Account:
    account = make_account()
    account.verify(occurred_at=NOW)
    for role in roles:
        account.grant(role)
    await repository.add(account)
    await session.commit()
    return account


async def test_roles_revoked_after_a_token_was_issued_take_effect_immediately(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    """The finding from Plan 1's Task 8 review, answered.

    A role encoded in the token would remain valid until the token expired. Reading roles
    from the database per request means an administrator's revocation binds on the very
    next call. A broken implementation that reads roles from the token, or caches the
    first lookup, would return EDITOR on the second assertion below — it must not.
    """
    account = await verified_account_with(session, repository, Role.EDITOR)
    token = tokens.issue_access(account.id)
    assert Role.EDITOR in (await identity.actor_for(token)).roles

    account.revoke(Role.EDITOR)
    await repository.save(account)
    await session.commit()

    assert Role.EDITOR not in (await identity.actor_for(token)).roles


async def test_roles_granted_after_a_token_was_issued_take_effect_immediately(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository)
    token = tokens.issue_access(account.id)
    assert Role.REVIEWER not in (await identity.actor_for(token)).roles

    account.grant(Role.REVIEWER)
    await repository.save(account)
    await session.commit()

    assert Role.REVIEWER in (await identity.actor_for(token)).roles


async def test_a_token_for_a_deleted_account_is_refused(
    identity: IdentityService, tokens: JwtTokenService
) -> None:
    token = tokens.issue_access(UserId(uuid4()))
    with pytest.raises(AuthenticationError, match="no account"):
        await identity.actor_for(token)


async def test_a_deactivated_account_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository)
    account.deactivate()
    await repository.save(account)
    await session.commit()

    token = tokens.issue_access(account.id)
    with pytest.raises(AuthenticationError):
        await identity.actor_for(token)


async def test_an_unverified_account_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = make_account()
    await repository.add(account)
    await session.commit()

    token = tokens.issue_access(account.id)
    with pytest.raises(AuthenticationError):
        await identity.actor_for(token)


async def test_an_expired_token_is_refused(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    """`InvalidTokenError`, not `AuthenticationError`: Step 2 makes `actor_for` let token
    errors propagate unwrapped, precisely so the API layer can tell "bad token" apart
    from "no such account". A test asserting `AuthenticationError` here would pass
    against an implementation that violated that contract, so it must not be written."""
    account = await verified_account_with(session, repository)
    token = tokens.issue_access(account.id)
    clock.moment += timedelta(minutes=16)

    with pytest.raises(InvalidTokenError, match="expired"):
        await identity.actor_for(token)


async def test_the_assembled_actor_id_equals_the_account_id(
    session: AsyncSession,
    repository: SqlAlchemyAccountRepository,
    identity: IdentityService,
    tokens: JwtTokenService,
) -> None:
    account = await verified_account_with(session, repository, Role.AUTHOR)
    token = tokens.issue_access(account.id)
    actor = await identity.actor_for(token)
    assert actor.id == account.id
```

Run: `cd backend && uv run pytest tests/integration/test_actor_assembly.py -v -m integration`
Expected: FAIL — `ModuleNotFoundError: No module named 'ugjcs.application.identity'`.

**A correction to this task, made explicit rather than silently carried forward.** An
earlier draft of this task asserted `AuthenticationError` for the expired-token case. That
contradicts Step 2 below, which deliberately lets `InvalidTokenError` propagate unwrapped. The
test above asserts the correct, intended behaviour: `InvalidTokenError`.

- [ ] **Step 2: Write the implementation**

Create `backend/src/ugjcs/application/identity.py`:

```python
"""Turning a credential into an `Actor` the authorisation layer can trust.

`policies.can()` trusts `Actor.roles` completely. That trust has to be earned somewhere,
and this is the only place it is: roles are read from the database on every request, never
taken from the token. The cost is one indexed query; the benefit is that revoking a role
binds immediately instead of whenever the holder's token happens to expire.
"""

from ugjcs.application.ports import AccountRepository, TokenService
from ugjcs.domain.errors import DomainError
from ugjcs.domain.policies import Actor


class AuthenticationError(DomainError):
    """The credential is valid in form but does not identify a usable account."""


class IdentityService:
    def __init__(self, accounts: AccountRepository, tokens: TokenService) -> None:
        self._accounts = accounts
        self._tokens = tokens

    async def actor_for(self, access_token: str) -> Actor:
        subject = self._tokens.read_access(access_token)
        account = await self._accounts.get(subject)
        if account is None:
            raise AuthenticationError("no account for this credential")
        if not account.may_authenticate():
            raise AuthenticationError("account is not permitted to authenticate")
        return Actor(id=account.id, roles=account.roles)
```

`InvalidTokenError` from Task 4 is already a `DomainError`; let it propagate rather than wrapping it, so the API layer in Plan 4 can distinguish "bad token" from "no such account" when choosing a status code. Do not add a `try/except InvalidTokenError` here — doing so would make `test_an_expired_token_is_refused` fail on the wrong exception type, which is the point of that test.

- [ ] **Step 3: Run, gate, commit**

Run: `cd backend && uv run pytest tests/integration/test_actor_assembly.py -v -m integration` — expect 7 tests to pass; report the actual count.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/application/identity.py backend/tests/integration/test_actor_assembly.py
git commit -m "feat: assemble actors with roles read fresh so revocation is immediate"
```

---

### Task 7: Registration and verification

**Files:**
- Create: `backend/src/ugjcs/infrastructure/email/__init__.py`, `backend/src/ugjcs/infrastructure/email/logging_sender.py`, `backend/tests/unit/application/__init__.py`, `backend/tests/unit/application/test_identity.py`
- Modify: `backend/src/ugjcs/application/identity.py`, `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/security/tokens.py`

**Interfaces:**
- Produces: `RegistrationService.register(...)`, `.verify(token)`; `LoggingEmailSender`; `TokenService.issue_verification`/`.read_verification`.

**Scope decision, recorded rather than assumed:** the verification *flow* is built in full behind the `EmailSender` port, but the only adapter shipped is `LoggingEmailSender`, which writes the verification link to the application log. Amazon SES in sandbox mode can only send to pre-verified addresses, which would fail for an assessor's inbox on demonstration day. Test accounts are therefore seeded pre-verified, and "replace `LoggingEmailSender` with an SES adapter and leave the sandbox" is entered in the technical debt register as **Scheduled**.

**Verification-token decision, made explicit rather than left open:** verification tokens
reuse `TokenService`, via two new methods (`issue_verification`/`read_verification`) added
alongside `issue_access`/`read_access`, signing a JWT with `typ="verify"` and a 48-hour
lifetime instead of the access token's 15 minutes. A *separate* opaque-and-hashed token
was the other option, but it would need its own storage — a row somewhere recording
`(token_hash, user_id, expires_at)` — purely to answer "is this token still good", when
`Account.verify()` (Task 1) already answers exactly that: it raises `AccountError` the
second time it is called on the same account. Reusing the signed-token machinery costs one
new pair of methods on an existing service; the opaque-token alternative costs a new table,
a new repository, and a new port for no additional guarantee. This is also why the unit
tests below need no fourth fake — `JwtTokenService` has no I/O and drops into a unit test
exactly like `Argon2PasswordHasher` already does in Task 3's tests.

- [ ] **Step 1: Extend the token service**

Append to `backend/src/ugjcs/infrastructure/security/tokens.py`, alongside `ACCESS_TYPE`:

```python
VERIFY_TYPE = "verify"
DEFAULT_VERIFICATION_TTL = timedelta(hours=48)
```

Add a keyword-only, defaulted parameter to `JwtTokenService.__init__` — existing callers
that only pass `secret`, `clock`, `access_ttl` and `refresh_ttl` are unaffected:

```python
    def __init__(
        self,
        *,
        secret: str,
        clock: Clock,
        access_ttl: timedelta,
        refresh_ttl: timedelta,
        verification_ttl: timedelta = DEFAULT_VERIFICATION_TTL,
    ) -> None:
        self._secret = secret
        self._clock = clock
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._verification_ttl = verification_ttl
```

Add the two methods, mirroring `issue_access`/`read_access`:

```python
    def issue_verification(self, subject: UserId) -> str:
        issued = self._clock.now()
        return jwt.encode(
            {
                "sub": str(subject),
                "typ": VERIFY_TYPE,
                "iat": int(issued.timestamp()),
                "exp": int((issued + self._verification_ttl).timestamp()),
            },
            self._secret,
            algorithm=ALGORITHM,
        )

    def read_verification(self, token: str) -> UserId:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[ALGORITHM])
        except jwt.ExpiredSignatureError as error:
            raise InvalidTokenError("verification link has expired") from error
        except jwt.PyJWTError as error:
            raise InvalidTokenError("verification link is not valid") from error
        if claims.get("typ") != VERIFY_TYPE:
            raise InvalidTokenError("wrong token type for verification")
        try:
            return UserId(UUID(claims["sub"]))
        except (KeyError, ValueError) as error:
            raise InvalidTokenError("token subject is missing or malformed") from error
```

- [ ] **Step 2: Extend the ports**

Append two methods to the `TokenService` protocol in `ports.py`, next to `issue_access`/`read_access`:

```python
    def issue_verification(self, subject: UserId) -> str: ...

    def read_verification(self, token: str) -> UserId:
        """Return the subject, or raise `InvalidTokenError` if absent, expired, replayed-typed,
        or of the wrong `typ`."""
        ...
```

- [ ] **Step 3: Write the failing tests**

Create `backend/tests/unit/application/__init__.py` (empty) and `backend/tests/unit/application/test_identity.py`:

```python
"""Unit tests for registration and verification, entirely in memory."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ugjcs.domain.account import Account, AccountError, EmailAddress
from ugjcs.domain.ids import UserId
from ugjcs.application.identity import RegistrationService
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import InvalidTokenError, JwtTokenService

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


class DictAccountRepository:
    """A dict-backed fake satisfying the `AccountRepository` protocol."""

    def __init__(self) -> None:
        self._by_id: dict[UserId, Account] = {}

    async def add(self, account: Account) -> None:
        self._by_id[account.id] = account

    async def get(self, user_id: UserId) -> Account | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: EmailAddress) -> Account | None:
        return next((a for a in self._by_id.values() if a.email.value == email.value), None)

    async def save(self, account: Account) -> None:
        if account.id not in self._by_id:
            raise LookupError(f"account {account.id} has never been persisted")
        self._by_id[account.id] = account


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_verification(self, to: str, link: str) -> None:
        self.sent.append((to, link))


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class CountingHasher:
    """Spies on `hash` calls so "no hashing occurred" can be asserted directly."""

    def __init__(self) -> None:
        self._inner = Argon2PasswordHasher()
        self.hash_calls = 0

    def hash(self, password: str) -> str:
        self.hash_calls += 1
        return self._inner.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._inner.verify(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._inner.needs_rehash(password_hash)


def make_service(
    accounts: DictAccountRepository | None = None,
    emails: FakeEmailSender | None = None,
    hasher: Argon2PasswordHasher | CountingHasher | None = None,
) -> tuple[RegistrationService, DictAccountRepository, FakeEmailSender]:
    accounts = accounts or DictAccountRepository()
    emails = emails or FakeEmailSender()
    tokens = JwtTokenService(
        secret="test-secret-not-used-anywhere-real",
        clock=FrozenClock(NOW),
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )
    service = RegistrationService(accounts, tokens, hasher or Argon2PasswordHasher(), emails, FrozenClock(NOW))
    return service, accounts, emails


async def test_registering_creates_an_unverified_account_and_sends_one_message() -> None:
    service, accounts, emails = make_service()
    account = await service.register(
        email="r.obeng@ug.edu.gh",
        password=PASSWORD,
        full_name="Roger Koranteng Obeng",
        affiliation="University of Ghana",
    )
    assert not account.is_verified
    assert len(emails.sent) == 1
    assert emails.sent[0][0] == "r.obeng@ug.edu.gh"


async def test_the_stored_password_hash_is_not_the_plaintext_password() -> None:
    service, accounts, _ = make_service()
    account = await service.register(
        email="hash@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    assert account.password_hash != PASSWORD


async def test_registering_an_existing_email_raises_and_sends_no_second_message() -> None:
    service, accounts, emails = make_service()
    await service.register(
        email="dup@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    with pytest.raises(AccountError, match="already exists"):
        await service.register(
            email="dup@ug.edu.gh", password=PASSWORD, full_name="B", affiliation="UG"
        )
    assert len(emails.sent) == 1


async def test_registering_an_email_differing_only_in_case_is_a_duplicate() -> None:
    service, accounts, emails = make_service()
    await service.register(
        email="Case@UG.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    with pytest.raises(AccountError, match="already exists"):
        await service.register(
            email="case@ug.edu.gh", password=PASSWORD, full_name="B", affiliation="UG"
        )
    assert len(emails.sent) == 1


async def test_a_valid_verification_token_verifies_the_account() -> None:
    service, accounts, emails = make_service()
    account = await service.register(
        email="verify@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    link = emails.sent[0][1]
    token = link.rsplit("=", 1)[-1]

    await service.verify(token)

    stored = await accounts.get(account.id)
    assert stored is not None
    assert stored.is_verified


async def test_a_verification_token_cannot_be_replayed() -> None:
    service, accounts, emails = make_service()
    await service.register(
        email="replay@ug.edu.gh", password=PASSWORD, full_name="A", affiliation="UG"
    )
    token = emails.sent[0][1].rsplit("=", 1)[-1]
    await service.verify(token)

    with pytest.raises(AccountError, match="already verified"):
        await service.verify(token)


async def test_an_unknown_verification_token_raises() -> None:
    service, _, _ = make_service()
    with pytest.raises(InvalidTokenError):
        await service.verify("not-a-real-token")


async def test_a_short_password_is_refused_before_any_hashing_occurs() -> None:
    hasher = CountingHasher()
    service, accounts, emails = make_service(hasher=hasher)
    with pytest.raises(AccountError, match="at least 12"):
        await service.register(
            email="short@ug.edu.gh", password="short", full_name="A", affiliation="UG"
        )
    assert hasher.hash_calls == 0
    assert await accounts.get_by_email(EmailAddress("short@ug.edu.gh")) is None
    assert emails.sent == []
```

Run: `cd backend && uv run pytest tests/unit/application/test_identity.py -v`
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name 'RegistrationService'`.

- [ ] **Step 4: Write the implementation**

Append to `backend/src/ugjcs/application/identity.py`. Extend its imports with `from uuid import uuid4`, `from ugjcs.application.ports import Clock, EmailSender, PasswordHasher` (alongside the existing `AccountRepository, TokenService`), and `from ugjcs.domain.account import Account, AccountError, EmailAddress`.

```python
MIN_PASSWORD_LENGTH = 12
"""NIST SP 800-63B: length predicts resistance to guessing better than composition rules
ever did. Deliberately no uppercase/digit/symbol requirement is imposed here."""

VERIFICATION_LINK_BASE = "https://ugjcs.example.edu/verify?token"


class RegistrationService:
    def __init__(
        self,
        accounts: AccountRepository,
        tokens: TokenService,
        hasher: PasswordHasher,
        emails: EmailSender,
        clock: Clock,
    ) -> None:
        self._accounts = accounts
        self._tokens = tokens
        self._hasher = hasher
        self._emails = emails
        self._clock = clock

    async def register(
        self, *, email: str, password: str, full_name: str, affiliation: str
    ) -> Account:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise AccountError(f"password must be at least {MIN_PASSWORD_LENGTH} characters")
        normalised = EmailAddress(email)
        if await self._accounts.get_by_email(normalised) is not None:
            raise AccountError(f"an account already exists for {normalised.value}")
        account = Account(
            id=UserId(uuid4()),
            email=normalised,
            password_hash=self._hasher.hash(password),
            full_name=full_name,
            affiliation=affiliation,
        )
        await self._accounts.add(account)
        token = self._tokens.issue_verification(account.id)
        await self._emails.send_verification(normalised.value, f"{VERIFICATION_LINK_BASE}={token}")
        return account

    async def verify(self, token: str) -> None:
        subject = self._tokens.read_verification(token)
        account = await self._accounts.get(subject)
        if account is None:
            raise AuthenticationError("no account for this verification link")
        account.verify(occurred_at=self._clock.now())
        await self._accounts.save(account)
```

Replay is refused for free: a second `verify()` call re-invokes `Account.verify()` on an
already-verified account, which Task 1 already makes raise `AccountError`. No separate
"has this token been used" bookkeeping is needed — this is the saving the scope decision
above described.

Create `backend/src/ugjcs/infrastructure/email/__init__.py` (empty) and `backend/src/ugjcs/infrastructure/email/logging_sender.py`:

```python
"""Stands in for a real mail transport. See Plan 3 Task 7's scope decision: SES sandbox
mode cannot reach an unverified assessor inbox, so verification links are logged instead.
"""

import logging

logger = logging.getLogger(__name__)


class LoggingEmailSender:
    async def send_verification(self, to: str, link: str) -> None:
        logger.info("verification link for %s: %s", to, link)
```

- [ ] **Step 5: Run, gate, commit**

Run: `cd backend && uv run pytest tests/unit/application/test_identity.py -v` — expect 8 tests to pass; report the actual count.
Run: `cd backend && make check`.

```bash
git add backend/src/ugjcs/application/identity.py backend/src/ugjcs/application/ports.py backend/src/ugjcs/infrastructure/security/tokens.py backend/src/ugjcs/infrastructure/email backend/tests/unit/application
git commit -m "feat: add registration with pluggable verification delivery"
```

---

### Task 8: Login, refresh rotation and reuse detection

**Files:**
- Create: `backend/src/ugjcs/infrastructure/db/refresh_token_repository.py`, `backend/tests/integration/test_refresh_rotation.py`
- Modify: `backend/src/ugjcs/application/identity.py`, `backend/src/ugjcs/application/ports.py`, `backend/src/ugjcs/infrastructure/db/mappers.py`, `backend/src/ugjcs/infrastructure/db/uow.py`

**Interfaces:**
- Produces: `TokenPair`; `RefreshTokenRecord`; `RefreshTokenRepository` protocol with `add`, `get_by_hash`, `revoke`, `revoke_family`; `SqlAlchemyRefreshTokenRepository`; `SessionService(accounts: AccountRepository, refresh_tokens: RefreshTokenRepository, tokens: TokenService, hasher: PasswordHasher, clock: Clock)` with `.log_in(email, password) -> TokenPair`, `.refresh(token) -> TokenPair`, `.log_out(token) -> None`.

**A gap this task closes, made explicit rather than left for the next plan to guess.**
`SessionService` needs somewhere to persist the `refresh_tokens` rows Task 2 already
created — family, hash, issued/expiry/revoked timestamps, the rotation chain. Neither
`AccountRepository` (Task 5) nor anything else in this plan owns that table, and
`SessionService` lives in `application/identity.py`, which may not import
`infrastructure` to reach `RefreshTokenRow` directly. This task therefore adds a
`RefreshTokenRepository` port — `AccountRepository`'s sibling, same shape of protocol,
same `UnitOfWork.refresh_tokens` pattern — and a `SqlAlchemyRefreshTokenRepository`
adapter. `SessionService`'s constructor is **`(accounts, refresh_tokens, tokens, hasher,
clock)`**, five positional dependencies, all ports. Downstream consumers (Plan 4) should
wire against this signature, not a guess.

`TokenService` is also missing one thing `SessionService` needs: a way to know how long a
refresh token should live when writing its `expires_at`. `JwtTokenService` already exposes
`refresh_ttl` as a property (Task 4), but the `TokenService` *protocol* Task 1 wrote never
declared it — an omission this task closes by adding the property to the protocol, so
`SessionService` can depend on the port rather than the concrete class.

- [ ] **Step 1: Extend the ports**

Append to `backend/src/ugjcs/application/ports.py`. Extend its imports with `from dataclasses import dataclass` and `from datetime import timedelta` (alongside the existing `datetime` import).

Add the missing property to `TokenService`:

```python
class TokenService(Protocol):
    ...

    @property
    def refresh_ttl(self) -> timedelta:
        """How long a freshly issued refresh token is valid, for computing its DB expiry."""
        ...
```

Add the record type and the new protocol:

```python
@dataclass(frozen=True, slots=True)
class RefreshTokenRecord:
    """A `refresh_tokens` row, as far as the application layer needs to see it."""

    id: UUID
    user_id: UserId
    family_id: UUID
    token_hash: str
    issued_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by: UUID | None


class RefreshTokenRepository(Protocol):
    async def add(self, record: RefreshTokenRecord) -> None: ...

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None: ...

    async def revoke(self, token_id: UUID, *, replaced_by: UUID | None = None) -> None:
        """Mark a single token spent. `replaced_by` records the row that superseded it."""
        ...

    async def revoke_family(self, family_id: UUID) -> None:
        """Revoke every unrevoked token sharing this family — the reuse-detection response."""
        ...
```

Add `accounts`' sibling to `UnitOfWork`:

```python
class UnitOfWork(Protocol):
    manuscripts: ManuscriptRepository
    accounts: AccountRepository
    refresh_tokens: RefreshTokenRepository
    ...
```

- [ ] **Step 2: Write the mappers and the repository**

Append to `backend/src/ugjcs/infrastructure/db/mappers.py`. Extend its imports with `RefreshTokenRow` from `ugjcs.infrastructure.db.models` and `RefreshTokenRecord` from `ugjcs.application.ports`.

```python
def refresh_token_to_row(record: RefreshTokenRecord) -> RefreshTokenRow:
    return RefreshTokenRow(
        id=record.id,
        user_id=record.user_id,
        family_id=record.family_id,
        token_hash=record.token_hash,
        issued_at=record.issued_at,
        expires_at=record.expires_at,
        revoked_at=record.revoked_at,
        replaced_by=record.replaced_by,
    )


def row_to_refresh_token(row: RefreshTokenRow) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=row.id,
        user_id=UserId(row.user_id),
        family_id=row.family_id,
        token_hash=row.token_hash,
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        replaced_by=row.replaced_by,
    )
```

Create `backend/src/ugjcs/infrastructure/db/refresh_token_repository.py`:

```python
"""PostgreSQL implementation of the refresh token repository port."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.ports import RefreshTokenRecord
from ugjcs.infrastructure.db.mappers import refresh_token_to_row, row_to_refresh_token
from ugjcs.infrastructure.db.models import RefreshTokenRow


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RefreshTokenRecord) -> None:
        self._session.add(refresh_token_to_row(record))

    async def get_by_hash(self, token_hash: str) -> RefreshTokenRecord | None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(RefreshTokenRow.token_hash == token_hash)
        )
        row = result.scalar_one_or_none()
        return row_to_refresh_token(row) if row is not None else None

    async def revoke(self, token_id: UUID, *, replaced_by: UUID | None = None) -> None:
        row = await self._session.get(RefreshTokenRow, token_id)
        if row is None:
            raise LookupError(f"refresh token {token_id} has never been persisted")
        row.revoked_at = datetime.now(UTC)
        row.replaced_by = replaced_by

    async def revoke_family(self, family_id: UUID) -> None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(
                RefreshTokenRow.family_id == family_id, RefreshTokenRow.revoked_at.is_(None)
            )
        )
        now = datetime.now(UTC)
        for row in result.scalars():
            row.revoked_at = now
```

Modify `backend/src/ugjcs/infrastructure/db/uow.py` the same way Task 5 wired `accounts`:

```python
class SqlAlchemyUnitOfWork:
    manuscripts: SqlAlchemyManuscriptRepository
    accounts: SqlAlchemyAccountRepository
    refresh_tokens: SqlAlchemyRefreshTokenRepository

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self.manuscripts = SqlAlchemyManuscriptRepository(self._session)
        self.accounts = SqlAlchemyAccountRepository(self._session)
        self.refresh_tokens = SqlAlchemyRefreshTokenRepository(self._session)
        return self
```

- [ ] **Step 3: Write the failing tests**

Create `backend/tests/integration/test_refresh_rotation.py`:

```python
"""Integration tests for login, refresh rotation and reuse detection."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ugjcs.application.identity import AuthenticationError, SessionService
from ugjcs.domain.account import Account, EmailAddress
from ugjcs.domain.ids import UserId
from ugjcs.infrastructure.db.account_repository import SqlAlchemyAccountRepository
from ugjcs.infrastructure.db.refresh_token_repository import SqlAlchemyRefreshTokenRepository
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService

pytestmark = pytest.mark.integration

NOW = datetime(2026, 8, 12, 9, 0, tzinfo=UTC)
PASSWORD = "correct horse battery staple"


class FrozenClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class CountingHasher:
    """Spies on `verify` calls. A wall-clock timing assertion would be flaky under CI
    load; this proves the same code path — a real Argon2 verify — runs for both a wrong
    password and an unregistered email, which is what makes the timing comparable."""

    def __init__(self) -> None:
        self._inner = Argon2PasswordHasher()
        self.verify_calls = 0

    def hash(self, password: str) -> str:
        return self._inner.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        self.verify_calls += 1
        return self._inner.verify(password, password_hash)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._inner.needs_rehash(password_hash)


@pytest.fixture
def clock() -> FrozenClock:
    return FrozenClock(NOW)


@pytest.fixture
def tokens(clock: FrozenClock) -> JwtTokenService:
    return JwtTokenService(
        secret="test-secret-not-used-anywhere-real",
        clock=clock,
        access_ttl=timedelta(minutes=15),
        refresh_ttl=timedelta(days=7),
    )


@pytest.fixture
def accounts(session: AsyncSession) -> SqlAlchemyAccountRepository:
    return SqlAlchemyAccountRepository(session)


@pytest.fixture
def refresh_tokens(session: AsyncSession) -> SqlAlchemyRefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


async def register_account(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    *,
    email: str = "r.obeng@ug.edu.gh",
    password: str = PASSWORD,
    verified: bool = True,
    active: bool = True,
    hasher: Argon2PasswordHasher | None = None,
) -> Account:
    account = Account(
        id=UserId(uuid4()),
        email=EmailAddress(email),
        password_hash=(hasher or Argon2PasswordHasher()).hash(password),
        full_name="Roger Koranteng Obeng",
        affiliation="University of Ghana",
    )
    if verified:
        account.verify(occurred_at=NOW)
    if not active:
        account.deactivate()
    await accounts.add(account)
    await session.commit()
    return account


def make_service(
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
    hasher: Argon2PasswordHasher | CountingHasher | None = None,
) -> SessionService:
    return SessionService(accounts, refresh_tokens, tokens, hasher or Argon2PasswordHasher(), clock)


async def test_correct_credentials_return_an_access_and_a_refresh_token(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    account = await register_account(session, accounts)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    pair = await service.log_in(account.email.value, PASSWORD)

    assert pair.access_token
    assert pair.refresh_token
    assert tokens.read_access(pair.access_token) == account.id


async def test_an_unknown_email_fails_like_a_wrong_password(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts)
    hasher = CountingHasher()
    service = make_service(accounts, refresh_tokens, tokens, clock, hasher)

    with pytest.raises(AuthenticationError) as unknown_error:
        await service.log_in("nobody@ug.edu.gh", "whatever-password")
    assert hasher.verify_calls == 1

    with pytest.raises(AuthenticationError) as wrong_error:
        await service.log_in("r.obeng@ug.edu.gh", "not the right password")
    assert hasher.verify_calls == 2

    assert str(unknown_error.value) == str(wrong_error.value)


async def test_an_unverified_account_cannot_log_in(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="unverified@ug.edu.gh", verified=False)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    with pytest.raises(AuthenticationError):
        await service.log_in("unverified@ug.edu.gh", PASSWORD)


async def test_a_deactivated_account_cannot_log_in(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="deactivated@ug.edu.gh", active=False)
    service = make_service(accounts, refresh_tokens, tokens, clock)

    with pytest.raises(AuthenticationError):
        await service.log_in("deactivated@ug.edu.gh", PASSWORD)


async def test_refreshing_returns_a_new_pair_and_the_old_token_stops_working(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    account = await register_account(session, accounts, email="rotate@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    first = await service.log_in("rotate@ug.edu.gh", PASSWORD)

    second = await service.refresh(first.refresh_token)

    assert second.refresh_token != first.refresh_token
    assert tokens.read_access(second.access_token) == account.id
    with pytest.raises(AuthenticationError):
        await service.refresh(first.refresh_token)


async def test_replaying_a_rotated_refresh_token_revokes_the_entire_family(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="reuse@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    first = await service.log_in("reuse@ug.edu.gh", PASSWORD)
    second = await service.refresh(first.refresh_token)

    # Replaying the spent token is theft-or-replay; the whole family dies, including the
    # newest, legitimately rotated token. An implementation that revoked only the
    # presented token would leave `second` usable — this is what that would miss.
    with pytest.raises(AuthenticationError):
        await service.refresh(first.refresh_token)

    with pytest.raises(AuthenticationError):
        await service.refresh(second.refresh_token)


async def test_an_expired_refresh_token_is_refused(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="expiring@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    pair = await service.log_in("expiring@ug.edu.gh", PASSWORD)

    clock.moment += timedelta(days=8)

    with pytest.raises(AuthenticationError, match="expired"):
        await service.refresh(pair.refresh_token)


async def test_logging_out_revokes_the_presented_tokens_family(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    await register_account(session, accounts, email="logout@ug.edu.gh")
    service = make_service(accounts, refresh_tokens, tokens, clock)
    pair = await service.log_in("logout@ug.edu.gh", PASSWORD)

    await service.log_out(pair.refresh_token)

    with pytest.raises(AuthenticationError):
        await service.refresh(pair.refresh_token)


async def test_a_successful_login_upgrades_an_outdated_password_hash(
    session: AsyncSession,
    accounts: SqlAlchemyAccountRepository,
    refresh_tokens: SqlAlchemyRefreshTokenRepository,
    tokens: JwtTokenService,
    clock: FrozenClock,
) -> None:
    weak_hasher = Argon2PasswordHasher(memory_cost=8, time_cost=1, parallelism=1)
    account = await register_account(session, accounts, email="weak@ug.edu.gh", hasher=weak_hasher)
    stored_before = account.password_hash
    service = make_service(accounts, refresh_tokens, tokens, clock)

    await service.log_in("weak@ug.edu.gh", PASSWORD)

    reloaded = await accounts.get(account.id)
    assert reloaded is not None
    assert reloaded.password_hash != stored_before
    assert Argon2PasswordHasher().verify(PASSWORD, reloaded.password_hash)
    assert not Argon2PasswordHasher().needs_rehash(reloaded.password_hash)
```

Run: `cd backend && uv run pytest tests/integration/test_refresh_rotation.py -v -m integration`
Expected: FAIL — `ImportError: cannot import name 'SessionService'`.

- [ ] **Step 4: Write the implementation**

Append to `backend/src/ugjcs/application/identity.py`. Extend its imports with `import secrets`, `from dataclasses import dataclass`, `from uuid import UUID`, and `from ugjcs.application.ports import RefreshTokenRecord, RefreshTokenRepository` (alongside the existing port imports).

```python
@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str


class SessionService:
    """Login and refresh-token lifecycle: issue, rotate, and detect reuse.

    Refresh rotation with reuse detection: each successful `refresh` issues a new token in
    the same family and marks the presented row `revoked_at` with `replaced_by` pointing at
    the new row's id. If a *revoked* row is presented again, that is either the legitimate
    holder retrying a request whose response was lost, or an attacker replaying a token they
    stole — the two cannot be told apart from here, so the entire family is revoked. Ending
    both sessions is the safe failure; leaving either one open is not.
    """

    def __init__(
        self,
        accounts: AccountRepository,
        refresh_tokens: RefreshTokenRepository,
        tokens: TokenService,
        hasher: PasswordHasher,
        clock: Clock,
    ) -> None:
        self._accounts = accounts
        self._refresh_tokens = refresh_tokens
        self._tokens = tokens
        self._hasher = hasher
        self._clock = clock
        # Hashed once per service instance, not per call, so an unregistered email still
        # pays the full Argon2 cost on every login attempt — the wall-clock gap between
        # "no such account" and "wrong password" is exactly what would let a caller
        # enumerate registered addresses.
        self._dummy_hash = hasher.hash(secrets.token_urlsafe(32))

    async def log_in(self, email: str, password: str) -> TokenPair:
        account = await self._accounts.get_by_email(EmailAddress(email))
        if account is None:
            self._hasher.verify(password, self._dummy_hash)
            raise AuthenticationError("email or password is incorrect")
        if not self._hasher.verify(password, account.password_hash):
            raise AuthenticationError("email or password is incorrect")
        if not account.may_authenticate():
            raise AuthenticationError("account is not permitted to authenticate")
        if self._hasher.needs_rehash(account.password_hash):
            account.password_hash = self._hasher.hash(password)
            await self._accounts.save(account)
        pair, _ = await self._issue_pair(account.id, family_id=uuid4())
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        token_hash = self._tokens.hash_refresh(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is None:
            raise AuthenticationError("refresh token is not recognised")
        if record.revoked_at is not None:
            await self._refresh_tokens.revoke_family(record.family_id)
            raise AuthenticationError("refresh token has already been used")
        if record.expires_at <= self._clock.now():
            raise AuthenticationError("refresh token has expired")
        pair, new_id = await self._issue_pair(record.user_id, family_id=record.family_id)
        await self._refresh_tokens.revoke(record.id, replaced_by=new_id)
        return pair

    async def log_out(self, refresh_token: str) -> None:
        token_hash = self._tokens.hash_refresh(refresh_token)
        record = await self._refresh_tokens.get_by_hash(token_hash)
        if record is not None:
            await self._refresh_tokens.revoke_family(record.family_id)

    async def _issue_pair(self, user_id: UserId, *, family_id: UUID) -> tuple[TokenPair, UUID]:
        access = self._tokens.issue_access(user_id)
        refresh, refresh_hash = self._tokens.issue_refresh(user_id, family_id)
        issued = self._clock.now()
        record_id = uuid4()
        await self._refresh_tokens.add(
            RefreshTokenRecord(
                id=record_id,
                user_id=user_id,
                family_id=family_id,
                token_hash=refresh_hash,
                issued_at=issued,
                expires_at=issued + self._tokens.refresh_ttl,
                revoked_at=None,
                replaced_by=None,
            )
        )
        return TokenPair(access_token=access, refresh_token=refresh), record_id
```

- [ ] **Step 5: Run, gate, commit**

Run: `cd backend && uv run pytest tests/integration/test_refresh_rotation.py -v -m integration` — expect 9 tests to pass; report the actual count.
Run: `cd backend && make check` and `cd backend && make integration`.

```bash
git add backend/src/ugjcs/application/identity.py backend/src/ugjcs/application/ports.py backend/src/ugjcs/infrastructure/db/mappers.py backend/src/ugjcs/infrastructure/db/refresh_token_repository.py backend/src/ugjcs/infrastructure/db/uow.py backend/tests/integration/test_refresh_rotation.py
git commit -m "feat: add login and refresh rotation with reuse detection"
```

---

## Definition of done for Plan 3

- `make check` green; `make integration` green.
- An account can register, be verified, log in, refresh, and log out.
- Passwords are Argon2id at OWASP parameters; no plaintext or hash is ever logged.
- Refresh tokens are stored only as hashes, rotate on use, and a replayed token revokes its family.
- **Revoking a role takes effect on the very next request**, proven by test, discharging Plan 1's Task 8 finding.
- Login does not disclose whether an email is registered.

## Deliberately not in this plan

HTTP routing, cookies and the Next.js BFF (Plan 4); password reset; multi-factor authentication; OAuth or ORCID federation; rate limiting, which belongs at the API edge where the client address is known.

## Entering the technical debt register from this plan

- **`LoggingEmailSender` in place of real delivery** → Cause: SES sandbox cannot reach unverified assessor inboxes within the 48-hour window → Impact: self-service verification does not work for real users; test accounts must be seeded pre-verified → Priority: Scheduled → Resolution: SES adapter plus production access request.
- **No rate limiting on login** → Cause: belongs at the API edge, which does not exist yet → Impact: online password guessing is unthrottled → Priority: **Critical before real users** → Resolution: Redis-backed limiter in Plan 4, per address and per account.
- **No password reset flow** → Cause: 48-hour scope → Impact: a locked-out user needs an administrator → Priority: Scheduled → Resolution: reuse the verification token machinery with a shorter lifetime.
