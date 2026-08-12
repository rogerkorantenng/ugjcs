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
VERIFY_TYPE = "verify"
DEFAULT_VERIFICATION_TTL = timedelta(hours=48)


class InvalidTokenError(DomainError):
    """A token that is absent, malformed, expired, of the wrong type, or not ours."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class JwtTokenService:
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
            claims = jwt.decode(
                token, self._secret, algorithms=[ALGORITHM], options={"verify_exp": False}
            )
        except jwt.PyJWTError as error:
            raise InvalidTokenError("token is not valid") from error
        if claims.get("exp", 0) <= self._clock.now().timestamp():
            raise InvalidTokenError("token has expired")
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

    @property
    def refresh_ttl(self) -> timedelta:
        return self._refresh_ttl
