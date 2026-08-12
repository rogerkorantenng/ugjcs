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
        self._hasher = Argon2(memory_cost=memory_cost, time_cost=time_cost, parallelism=parallelism)

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
