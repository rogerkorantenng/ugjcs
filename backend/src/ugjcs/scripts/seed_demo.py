"""Seed a demo corpus and five pre-verified judge accounts.

Runs inside the container on every boot (`backend/entrypoint.sh`), after migrations and
before the server starts accepting traffic. Idempotent by construction, not merely by a
one-shot flag: every account and every manuscript is looked up by its natural key before
being written, so re-running this — on every container restart, which is exactly what
happens — creates nothing twice and never raises on a record that already exists.
`--if-empty` (the flag the entrypoint always passes) only adds a fast path that skips the
lookups entirely once the administrator account is already present, verified, and holds
its role; it is a performance optimisation, not what makes re-running safe.

Accounts are created through `RegistrationService.register` and `Account.grant` /
`Account.verify` — the same machinery a real registration flow uses — so a seeded account
is indistinguishable in the database from one that self-registered and was verified by an
editor. Nothing here writes a row directly.

Credentials are intentionally fixed, not generated, and are also written verbatim into
Deployment_and_Source_Links.txt: this is an assessment corpus for an examiner to log into,
not a production tenant, so there is nothing to keep secret about them beyond the AWS
account itself.
"""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ugjcs.application.identity import RegistrationService
from ugjcs.domain.account import AccountError, EmailAddress
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.config import Settings, get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.email.logging_sender import LoggingEmailSender
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService, SystemClock

# Fixed, documented passwords for the five judge accounts, one constant per role so a
# reviewer of this file (or Deployment_and_Source_Links.txt, which quotes these verbatim)
# can see exactly what is being granted to whom. All are >= 12 characters, mix case,
# digits and punctuation, and satisfy RegistrationService.MIN_PASSWORD_LENGTH.
AUTHOR_PASSWORD = "Ugjcs-Author-2026!"
REVIEWER_PASSWORD = "Ugjcs-Reviewer-2026!"
EDITOR_PASSWORD = "Ugjcs-Editor-2026!"
EDITOR_IN_CHIEF_PASSWORD = "Ugjcs-EditorChief-2026!"
ADMINISTRATOR_PASSWORD = "Ugjcs-Admin-2026!"

ADMIN_EMAIL = "admin@ugjcs.test"

# (email, password, role, full name) — one row per judge account.
JUDGE_ACCOUNTS: list[tuple[str, str, Role, str]] = [
    ("author@ugjcs.test", AUTHOR_PASSWORD, Role.AUTHOR, "Ama Serwaa"),
    ("reviewer@ugjcs.test", REVIEWER_PASSWORD, Role.REVIEWER, "Kwabena Owusu"),
    ("editor@ugjcs.test", EDITOR_PASSWORD, Role.EDITOR, "Efua Mensah"),
    ("eic@ugjcs.test", EDITOR_IN_CHIEF_PASSWORD, Role.EDITOR_IN_CHIEF, "Kofi Boateng"),
    (ADMIN_EMAIL, ADMINISTRATOR_PASSWORD, Role.ADMINISTRATOR, "Abena Osei"),
]

# The demo corpus. The tracking-code year is fixed, not derived from the wall clock at
# boot time: minting by `datetime.now().year` would mean a container that happens to
# start after a New Year rolls over mints codes with a different year prefix, finds no
# existing manuscript under that new code, and creates a duplicate — exactly what
# idempotency is supposed to rule out.
SEED_TRACKING_YEAR = 2026
DEMO_TITLES = [
    "Sparse Retrieval for Low-Resource Languages",
    "Fair Scheduling for Shared GPU Clusters",
    "Edge Caching for Campus Networks",
]

NOW = datetime.now(UTC)


def _build_registration_service(
    uow: SqlAlchemyUnitOfWork, settings: Settings
) -> RegistrationService:
    tokens = JwtTokenService(
        secret=settings.jwt_secret,
        clock=SystemClock(),
        access_ttl=timedelta(minutes=settings.access_token_minutes),
        refresh_ttl=timedelta(days=settings.refresh_token_days),
    )
    return RegistrationService(
        uow.accounts, tokens, Argon2PasswordHasher(), LoggingEmailSender(), SystemClock()
    )


async def _fully_seeded(uow: SqlAlchemyUnitOfWork) -> bool:
    """Fast-path check: is the administrator account already usable?

    Only used to skip work early under `--if-empty`; the per-record checks in
    `_ensure_accounts` and `_ensure_demo_corpus` are what actually make re-running safe,
    so a `False` here never risks a duplicate — it only ever does a little more work.
    """
    admin = await uow.accounts.get_by_email(EmailAddress(ADMIN_EMAIL))
    return admin is not None and admin.is_verified and Role.ADMINISTRATOR in admin.roles


async def _ensure_accounts(
    uow: SqlAlchemyUnitOfWork, registration: RegistrationService
) -> dict[str, UserId]:
    """Create or reuse each judge account, granting its role and verifying it.

    `RegistrationService.register` itself raises `AccountError` for an email already on
    file, so a lookup-then-register race is caught rather than crashing the boot.
    """
    ids: dict[str, UserId] = {}
    for email, password, role, full_name in JUDGE_ACCOUNTS:
        normalised = EmailAddress(email)
        account = await uow.accounts.get_by_email(normalised)
        if account is None:
            try:
                account = await registration.register(
                    email=email,
                    password=password,
                    full_name=full_name,
                    affiliation="University of Ghana",
                )
            except AccountError:
                existing = await uow.accounts.get_by_email(normalised)
                if existing is None:
                    raise
                account = existing

        changed = False
        if role not in account.roles:
            account.grant(role)
            changed = True
        if not account.is_verified:
            account.verify(occurred_at=NOW)
            changed = True
        if changed:
            await uow.accounts.save(account)

        ids[email] = account.id
    return ids


async def _ensure_demo_corpus(uow: SqlAlchemyUnitOfWork, *, author_id: UserId) -> int:
    """Create any demo manuscript not already present under its tracking code.

    Returns the number of manuscripts actually created, for the summary line.
    """
    created = 0
    for sequence, title in enumerate(DEMO_TITLES, start=1):
        code = TrackingCode.mint(SEED_TRACKING_YEAR, sequence)
        if await uow.manuscripts.get_by_tracking_code(code) is not None:
            continue
        manuscript = Manuscript(
            id=ManuscriptId(uuid4()),
            tracking_code=code,
            title=title,
            abstract=f"A demonstration submission seeded for assessment: {title}.",
            keywords=("demo",),
            author_ids=(author_id,),
            corresponding_author_id=author_id,
        )
        manuscript.submit(actor_id=author_id, occurred_at=NOW)
        await uow.manuscripts.add(manuscript)
        created += 1
    return created


async def run(*, only_if_empty: bool) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, echo=False)
    factory = session_factory(engine)
    try:
        async with SqlAlchemyUnitOfWork(factory) as uow:
            if only_if_empty and await _fully_seeded(uow):
                print("Demo data already present; skipping.")
                return
            registration = _build_registration_service(uow, settings)
            ids = await _ensure_accounts(uow, registration)
            created = await _ensure_demo_corpus(uow, author_id=ids["author@ugjcs.test"])
            await uow.commit()
            print(
                f"Ensured {len(JUDGE_ACCOUNTS)} judge account(s); "
                f"created {created} new demo manuscript(s)."
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--if-empty",
        action="store_true",
        default=False,
        help="Skip all work if the administrator account is already fully seeded.",
    )
    args = parser.parse_args()
    asyncio.run(run(only_if_empty=args.if_empty))


if __name__ == "__main__":
    main()
