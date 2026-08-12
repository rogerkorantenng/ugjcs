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
│   │   ├── ports.py                             Task 1  (extended) hasher, tokens, clock, email
│   │   └── identity.py                          Task 7  registration/login/refresh use cases
│   └── infrastructure/
│       ├── security/
│       │   ├── __init__.py                      Task 3
│       │   ├── passwords.py                     Task 3  Argon2id adapter
│       │   └── tokens.py                        Task 4  JWT access + rotating refresh
│       ├── email/
│       │   ├── __init__.py                      Task 7
│       │   └── logging_sender.py                Task 7  writes the link to the log
│       └── db/
│           ├── models.py                        Task 2  (extended) users, user_roles, refresh_tokens
│           ├── mappers.py                       Task 2  (extended) account mapping
│           └── account_repository.py            Task 5
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
        """Return the subject, or raise `InvalidToken` if absent, expired or tampered with."""
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
- Produces: `InvalidToken`, `JwtTokenService(secret, clock, access_ttl, refresh_ttl)`, `SystemClock`.

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
from ugjcs.infrastructure.security.tokens import InvalidToken, JwtTokenService

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
    with pytest.raises(InvalidToken, match="expired"):
        make_service(clock).read_access(token)


def test_a_token_signed_with_another_secret_is_refused() -> None:
    clock = FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC))
    token = make_service(clock).issue_access(SUBJECT)
    other = JwtTokenService(secret="a-different-secret", clock=clock,
                            access_ttl=timedelta(minutes=15), refresh_ttl=timedelta(days=7))
    with pytest.raises(InvalidToken):
        other.read_access(token)


def test_a_tampered_token_is_refused() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    token = service.issue_access(SUBJECT)
    with pytest.raises(InvalidToken):
        service.read_access(token[:-2] + ("aa" if not token.endswith("aa") else "bb"))


def test_rubbish_is_refused_rather_than_crashing() -> None:
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    with pytest.raises(InvalidToken):
        service.read_access("not.a.token")


def test_an_access_token_cannot_be_used_as_a_refresh_token() -> None:
    """Token confusion: a short-lived credential must not unlock a long-lived one."""
    service = make_service(FrozenClock(datetime(2026, 8, 12, 9, 0, tzinfo=UTC)))
    access = service.issue_access(SUBJECT)
    refresh, _ = service.issue_refresh(SUBJECT, uuid4())
    assert access != refresh
    with pytest.raises(InvalidToken, match="wrong token type"):
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


class InvalidToken(DomainError):
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
            raise InvalidToken("token has expired") from error
        except jwt.PyJWTError as error:
            raise InvalidToken("token is not valid") from error
        if claims.get("typ") != ACCESS_TYPE:
            raise InvalidToken("wrong token type for this endpoint")
        try:
            return UserId(UUID(claims["sub"]))
        except (KeyError, ValueError) as error:
            raise InvalidToken("token subject is missing or malformed") from error

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
- Modify: `backend/src/ugjcs/infrastructure/db/mappers.py`, `backend/src/ugjcs/application/ports.py`

**Interfaces:**
- Produces: `AccountRepository` protocol with `add`, `get`, `get_by_email`, `save`; `SqlAlchemyAccountRepository`; `account_to_row` and `row_to_account` mappers.

- [ ] **Step 1: Extend the ports**

Add an `AccountRepository` protocol to `ports.py` with `async def add(self, account: Account) -> None`, `async def get(self, user_id: UserId) -> Account | None`, `async def get_by_email(self, email: EmailAddress) -> Account | None`, and `async def save(self, account: Account) -> None`. Add `manuscripts`' sibling `accounts: AccountRepository` to the `UnitOfWork` protocol.

- [ ] **Step 2: Write the mappers**

Add `account_to_row(account) -> UserRow` and `row_to_account(row) -> Account` to `mappers.py`, following the existing style. `row_to_account` must populate `_roles` from `row.roles` — the same private-attribute assignment pattern, and for the same reason: a public setter would let any caller rewrite the role set.

- [ ] **Step 3: Write the failing integration test**

Create `backend/tests/integration/test_account_repository.py` with `pytestmark = pytest.mark.integration`, covering: a stored account reads back with its roles; lookup by email is case-insensitive (store `R.Obeng@UG.edu.gh`, fetch `r.obeng@ug.edu.gh`); a missing account returns `None`; granting a role and saving persists it; revoking a role and saving removes it; a duplicate email raises an integrity error.

- [ ] **Step 4: Write the repository**

Create `backend/src/ugjcs/infrastructure/db/account_repository.py` following `SqlAlchemyManuscriptRepository`'s shape: constructor takes an `AsyncSession`; `get_by_email` queries on the normalised value; `save` re-reads the row, updates scalar fields, and replaces the role rows to match `account.roles`.

- [ ] **Step 5: Run, gate, commit**

```bash
git add backend/src/ugjcs/infrastructure/db/account_repository.py backend/src/ugjcs/infrastructure/db/mappers.py backend/src/ugjcs/application/ports.py backend/tests/integration/test_account_repository.py
git commit -m "feat: persist accounts and their roles"
```

---

### Task 6: Actor assembly — the finding this plan answers

**Files:**
- Create: `backend/src/ugjcs/application/identity.py`, `backend/tests/integration/test_actor_assembly.py`

**Interfaces:**
- Produces: `AuthenticationError`; `IdentityService.actor_for(access_token) -> Actor`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_actor_assembly.py`, `pytestmark = pytest.mark.integration`. It must cover:

```python
async def test_roles_revoked_after_a_token_was_issued_take_effect_immediately(...) -> None:
    """The finding from Plan 1's Task 8 review, answered.

    A role encoded in the token would remain valid until the token expired. Reading roles
    from the database per request means an administrator's revocation binds on the very
    next call.
    """
    account = await verified_account_with(Role.EDITOR)
    token = tokens.issue_access(account.id)
    assert Role.EDITOR in (await identity.actor_for(token)).roles

    account.revoke(Role.EDITOR)
    await repository.save(account)
    await session.commit()

    assert Role.EDITOR not in (await identity.actor_for(token)).roles
```

Also cover: a role *granted* after issuance is likewise visible immediately; a token for a deleted account raises `AuthenticationError`; a deactivated account raises `AuthenticationError`; an unverified account raises `AuthenticationError`; an expired token raises `AuthenticationError`; the assembled `Actor.id` equals the account id.

Write these out in full, with the fixtures they need — do not leave them as prose.

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

`InvalidToken` from Task 4 is already a `DomainError`; let it propagate rather than wrapping it, so the API layer in Plan 4 can distinguish "bad token" from "no such account" when choosing a status code.

- [ ] **Step 3: Run, gate, commit**

```bash
git add backend/src/ugjcs/application/identity.py backend/tests/integration/test_actor_assembly.py
git commit -m "feat: assemble actors with roles read fresh so revocation is immediate"
```

---

### Task 7: Registration and verification

**Files:**
- Create: `backend/src/ugjcs/infrastructure/email/__init__.py`, `backend/src/ugjcs/infrastructure/email/logging_sender.py`, `backend/tests/unit/application/__init__.py`, `backend/tests/unit/application/test_identity.py`
- Modify: `backend/src/ugjcs/application/identity.py`

**Interfaces:**
- Produces: `RegistrationService.register(...)`, `.verify(token)`; `LoggingEmailSender`.

**Scope decision, recorded rather than assumed:** the verification *flow* is built in full behind the `EmailSender` port, but the only adapter shipped is `LoggingEmailSender`, which writes the verification link to the application log. Amazon SES in sandbox mode can only send to pre-verified addresses, which would fail for an assessor's inbox on demonstration day. Test accounts are therefore seeded pre-verified, and "replace `LoggingEmailSender` with an SES adapter and leave the sandbox" is entered in the technical debt register as **Scheduled**.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/unit/application/test_identity.py` using in-memory fakes (a dict-backed `AccountRepository`, a `FakeEmailSender` recording sent links, a `FrozenClock`). Cover:

- registering creates an unverified account and sends exactly one verification message
- the stored password hash is not the plaintext password
- registering an email that already exists raises, and does **not** send a second message
- registering with an email differing only in case is treated as a duplicate
- a valid verification token verifies the account
- a verification token cannot be replayed once used
- an unknown verification token raises
- registration with a password shorter than 12 characters is refused before any hashing occurs

Write them out in full with real assertions.

- [ ] **Step 2: Write the implementation**

Add `RegistrationService` to `application/identity.py` and create `LoggingEmailSender`. Enforce a 12-character minimum password length as a named constant with a comment citing NIST SP 800-63B's guidance that length matters more than composition rules — and deliberately impose no composition requirements.

Verification tokens reuse `TokenService.issue_access` with a distinct `typ`, or a separate opaque token stored hashed; either is acceptable, but state which you chose and why in your report.

- [ ] **Step 3: Run, gate, commit**

```bash
git add backend/src/ugjcs/application/identity.py backend/src/ugjcs/infrastructure/email backend/tests/unit/application
git commit -m "feat: add registration with pluggable verification delivery"
```

---

### Task 8: Login, refresh rotation and reuse detection

**Files:**
- Modify: `backend/src/ugjcs/application/identity.py`
- Create: `backend/tests/integration/test_refresh_rotation.py`

**Interfaces:**
- Produces: `SessionService.log_in(email, password) -> TokenPair`, `.refresh(token) -> TokenPair`, `.log_out(token)`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/integration/test_refresh_rotation.py`, `pytestmark = pytest.mark.integration`. Cover in full:

- correct credentials return an access and a refresh token
- an unknown email fails with the **same** error and comparable timing as a wrong password, so the endpoint cannot be used to enumerate registered users
- an unverified account cannot log in
- a deactivated account cannot log in
- refreshing returns a new pair and the old refresh token stops working
- **replaying an already-rotated refresh token revokes the entire family**, so the newest token stops working too
- an expired refresh token is refused
- logging out revokes the presented token's family
- a successful login with a password whose hash uses outdated parameters transparently upgrades the stored hash

- [ ] **Step 2: Write the implementation**

Refresh rotation with reuse detection works as follows, and the comment in the code should say so: each refresh issues a new token in the same family and marks the old row `revoked_at` with `replaced_by` pointing at the new row. If a token is presented whose row is already revoked, that is either theft or a replay — the entire family is revoked immediately, because the legitimate holder and the attacker cannot be told apart and ending both sessions is the safe failure.

Constant-time behaviour on unknown email: hash the supplied password against a dummy hash before returning the failure, so a missing account and a wrong password take comparable time.

- [ ] **Step 3: Run, gate, commit**

```bash
git add backend/src/ugjcs/application/identity.py backend/tests/integration/test_refresh_rotation.py
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
