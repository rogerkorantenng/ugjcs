from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher

PASSWORD = "correct horse battery staple"


def test_a_hash_is_not_the_password() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.hash(PASSWORD) != PASSWORD


def test_hashing_is_salted_so_two_hashes_differ() -> None:
    """Equal passwords must not produce equal hashes, or the database leaks which users
    share one."""
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
