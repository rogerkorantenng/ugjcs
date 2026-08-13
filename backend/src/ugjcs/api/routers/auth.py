"""Login, refresh, logout and the identity of the caller.

`/login` and `/refresh` are deliberately unauthenticated — a bearer token is exactly
what they are issuing. `/logout` is unauthenticated for the same reason `/refresh` is:
per `docs/05-api-contract.md` §6, it revokes by the refresh token carried in the body,
not by a bearer access token — an access token may already be expired at logout time,
and the refresh token's hash lookup is what identifies the session to revoke. Only `/me`
carries `get_current_actor`/`ActorDep` (via `Depends`), a marked authorisation
dependency; `/login`, `/refresh` and `/logout` are the three entries
`test_route_audit.py` allowlists as public for this router.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from ugjcs.api.deps import ActorDep
from ugjcs.api.wiring import UowDep, get_registration_service, get_session_service
from ugjcs.application.identity import RegistrationService, SessionService
from ugjcs.domain.enums import Role
from ugjcs.domain.policies import Actor

router = APIRouter()


class LoginRequest(BaseModel):
    # A plain `str`, not pydantic's `EmailStr`: `EmailStr` requires the `email-validator`
    # extra, which is not installed and cannot be added without editing `pyproject.toml`
    # (forbidden by this plan's Global Constraints). Format validation is unnecessary
    # here regardless — `SessionService.log_in` normalises through
    # `ugjcs.domain.account.EmailAddress` and an unregistered address already fails
    # identically to a wrong password.
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ActorOut(BaseModel):
    id: str
    roles: list[str]

    @classmethod
    def from_domain(cls, actor: Actor) -> "ActorOut":
        return cls(id=str(actor.id), roles=sorted(role.value for role in actor.roles))


SessionDep = Annotated[SessionService, Depends(get_session_service)]
RegistrationDep = Annotated[RegistrationService, Depends(get_registration_service)]


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    affiliation: str


@router.post("/register", response_model=TokenPairOut, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest, registration: RegistrationDep, sessions: SessionDep, uow: UowDep
) -> TokenPairOut:
    """Self-service sign-up, for authors only.

    The AUTHOR role is granted automatically — it is the one role the public may hold.
    Reviewer and editorial roles are appointed by the editorial office, never
    self-selected here. Email delivery is mocked in this prototype (the verification
    link is logged, not sent), so the account is verified immediately and signed in;
    password policy (length, not composition) is enforced by `RegistrationService`.
    """
    account = await registration.register(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        affiliation=body.affiliation,
    )
    account.grant(Role.AUTHOR)
    account.verify(occurred_at=datetime.now(UTC))
    await uow.accounts.save(account)
    await uow.commit()
    pair = await sessions.log_in(body.email, body.password)
    await uow.commit()
    return TokenPairOut(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/login", response_model=TokenPairOut)
async def log_in(body: LoginRequest, sessions: SessionDep) -> TokenPairOut:
    pair = await sessions.log_in(body.email, body.password)
    return TokenPairOut(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/refresh", response_model=TokenPairOut)
async def refresh(body: RefreshRequest, sessions: SessionDep) -> TokenPairOut:
    pair = await sessions.refresh(body.refresh_token)
    return TokenPairOut(access_token=pair.access_token, refresh_token=pair.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def log_out(body: RefreshRequest, sessions: SessionDep) -> None:
    await sessions.log_out(body.refresh_token)


@router.get("/me", response_model=ActorOut)
async def me(actor: ActorDep) -> ActorOut:
    return ActorOut.from_domain(actor)
