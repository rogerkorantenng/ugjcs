"""Seed a demo corpus and seven pre-verified judge accounts.

Runs inside the container on every boot (`backend/entrypoint.sh`), after migrations and
before the server starts accepting traffic. Idempotent by construction, not merely by a
one-shot flag: every account and every manuscript is looked up by its natural key before
being written, and every manuscript's lifecycle is *resumed* from whatever state it is
already in — driven forward one legal transition at a time until it reaches its target
status — so re-running this, on every container restart, which is exactly what happens,
creates nothing twice, never raises on a record that already exists, and never leaves a
manuscript stuck partway because a previous deploy only got it as far as `SUBMITTED`.
`--if-empty` (the flag the entrypoint always passes) only adds a fast path that skips the
lookups entirely once the administrator account *and* the full demo corpus are already
present; it is a performance optimisation, not what makes re-running safe — the per-record
and per-transition checks in `_ensure_accounts` and `_advance_manuscript` are what do that.

Accounts are created through `RegistrationService.register` and `Account.grant` /
`Account.verify` — the same machinery a real registration flow uses — so a seeded account
is indistinguishable in the database from one that self-registered and was verified by an
editor. Manuscripts are driven the same way: through `Manuscript.submit`,
`begin_screening`, `record_decision`, `record_review` and `schedule`/`publish` — the exact
aggregate methods the API routers call — plus `ReviewAssignmentRepository.assign` /
`mark_submitted` for the read model the reviewer's queue is built from. Nothing here
writes a row directly, so the event log, the hash chain and the audit trail are all
genuinely consistent, not merely populated.

Credentials are intentionally fixed, not generated, and are also written verbatim into
Deployment_and_Source_Links.txt: this is an assessment corpus for an examiner to log into,
not a production tenant, so there is nothing to keep secret about them beyond the AWS
account itself.
"""

import argparse
import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from ugjcs.application.identity import RegistrationService
from ugjcs.domain.account import AccountError, EmailAddress
from ugjcs.domain.enums import DecisionType, Role
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import IssueId, ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript
from ugjcs.infrastructure.config import Settings, get_settings
from ugjcs.infrastructure.db.engine import create_engine, session_factory
from ugjcs.infrastructure.db.uow import SqlAlchemyUnitOfWork
from ugjcs.infrastructure.email.logging_sender import LoggingEmailSender
from ugjcs.infrastructure.security.passwords import Argon2PasswordHasher
from ugjcs.infrastructure.security.tokens import JwtTokenService, SystemClock

# Fixed, documented passwords, one constant per role so a reviewer of this file (or
# Deployment_and_Source_Links.txt, which quotes these verbatim) can see exactly what is
# being granted to whom. All are >= 12 characters, mix case, digits and punctuation, and
# satisfy RegistrationService.MIN_PASSWORD_LENGTH.
AUTHOR_PASSWORD = "Ugjcs-Author-2026!"
AUTHOR2_PASSWORD = "Ugjcs-Author2-2026!"
REVIEWER_PASSWORD = "Ugjcs-Reviewer-2026!"
REVIEWER2_PASSWORD = "Ugjcs-Reviewer2-2026!"
EDITOR_PASSWORD = "Ugjcs-Editor-2026!"
EDITOR_IN_CHIEF_PASSWORD = "Ugjcs-EditorChief-2026!"
ADMINISTRATOR_PASSWORD = "Ugjcs-Admin-2026!"

ADMIN_EMAIL = "admin@ugjcs.test"
AUTHOR_EMAIL = "author@ugjcs.test"
AUTHOR2_EMAIL = "author2@ugjcs.test"
REVIEWER_EMAIL = "reviewer@ugjcs.test"
REVIEWER2_EMAIL = "reviewer2@ugjcs.test"
EDITOR_EMAIL = "editor@ugjcs.test"
EIC_EMAIL = "eic@ugjcs.test"

# (email, password, role, full name) — one row per judge account. Two author accounts and
# two reviewer accounts so the demo corpus can vary its bylines and give each review round
# two distinct reviewers, exactly as `record_review`'s quorum expects in a real newsroom.
JUDGE_ACCOUNTS: list[tuple[str, str, Role, str]] = [
    (AUTHOR_EMAIL, AUTHOR_PASSWORD, Role.AUTHOR, "Ama Serwaa"),
    (AUTHOR2_EMAIL, AUTHOR2_PASSWORD, Role.AUTHOR, "Kojo Antwi"),
    (REVIEWER_EMAIL, REVIEWER_PASSWORD, Role.REVIEWER, "Kwabena Owusu"),
    (REVIEWER2_EMAIL, REVIEWER2_PASSWORD, Role.REVIEWER, "Adjoa Boadi"),
    (EDITOR_EMAIL, EDITOR_PASSWORD, Role.EDITOR, "Efua Mensah"),
    (EIC_EMAIL, EDITOR_IN_CHIEF_PASSWORD, Role.EDITOR_IN_CHIEF, "Kofi Boateng"),
    (ADMIN_EMAIL, ADMINISTRATOR_PASSWORD, Role.ADMINISTRATOR, "Abena Osei"),
]

# The tracking-code year is fixed, not derived from the wall clock at boot time: minting
# by `datetime.now().year` would mean a container that happens to start after a New Year
# rolls over mints codes with a different year prefix, finds no existing manuscript under
# that new code, and creates a duplicate — exactly what idempotency is supposed to rule
# out.
SEED_TRACKING_YEAR = 2026

# A single demonstration issue every published paper in this corpus is scheduled into.
# Fixed rather than randomly generated per run, for the same reason the tracking year is
# fixed: `schedule` writes it into the event payload, and a stable value keeps that
# payload identical across a container restart that finds the paper already scheduled.
DEMO_ISSUE_ID = IssueId(UUID("00000000-0000-4000-8000-000000000001"))

NOW = datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ManuscriptSpec:
    """One demo manuscript: its content, byline, and how far it should travel.

    `reviewer_emails` is empty for a manuscript that never leaves screening (nothing to
    assign yet) and holds exactly two emails otherwise — the quorum `record_review`
    enforces. For `UNDER_REVIEW`, only the first of the two ever submits, which is what
    leaves the round open for the reviewer dashboard to show.
    """

    sequence: int
    title: str
    abstract: str
    keywords: tuple[str, ...]
    corresponding_author_email: str
    co_author_emails: tuple[str, ...]
    target: S
    reviewer_emails: tuple[str, ...] = ()


# Three manuscripts left mid-workflow — one per stage an editor or reviewer would actually
# see queued — and four driven all the way to PUBLISHED, so the public archive has content
# a citation could point at.
MANUSCRIPT_SPECS: tuple[ManuscriptSpec, ...] = (
    ManuscriptSpec(
        sequence=1,
        title="Sparse Retrieval for Low-Resource Languages",
        abstract=(
            "We study sparse lexical retrieval for Twi and Ga, two Ghanaian languages "
            "with little annotated text, and show that morphology-aware tokenisation "
            "narrows most of the gap to a dense retriever trained on English."
        ),
        keywords=("information retrieval", "low-resource NLP", "Ghanaian languages"),
        corresponding_author_email=AUTHOR_EMAIL,
        co_author_emails=(),
        target=S.SUBMITTED,
    ),
    ManuscriptSpec(
        sequence=2,
        title="Fair Scheduling for Shared GPU Clusters",
        abstract=(
            "We propose a weighted fair-share scheduler for GPU clusters shared between "
            "coursework and research jobs on a university compute grid, and evaluate it "
            "against first-come-first-served on the Department of Computer Science's own "
            "teaching cluster."
        ),
        keywords=("systems", "scheduling", "GPU clusters"),
        corresponding_author_email=AUTHOR2_EMAIL,
        co_author_emails=(AUTHOR_EMAIL,),
        target=S.UNDER_REVIEW,
        reviewer_emails=(REVIEWER_EMAIL, REVIEWER2_EMAIL),
    ),
    ManuscriptSpec(
        sequence=3,
        title="Edge Caching for Campus Networks",
        abstract=(
            "We measure lecture-video re-access patterns on a university campus network "
            "and show that a small edge cache placed at the hall-of-residence router "
            "removes most peak-hour backbone traffic at a fraction of a full CDN's cost."
        ),
        keywords=("networking", "edge caching", "campus networks"),
        corresponding_author_email=AUTHOR_EMAIL,
        co_author_emails=(),
        target=S.REVISION_REQUESTED,
    ),
    ManuscriptSpec(
        sequence=4,
        title="A Comparative Study of Mobile Money Fraud Detection Models in Ghana",
        abstract=(
            "Using anonymised transaction logs from three Ghanaian mobile money "
            "operators, we compare gradient-boosted trees against a graph neural network "
            "for detecting fraud rings, finding the graph model catches collusive rings "
            "the tree-based baseline misses entirely."
        ),
        keywords=("mobile money", "fraud detection", "graph neural networks"),
        corresponding_author_email=AUTHOR2_EMAIL,
        co_author_emails=(AUTHOR_EMAIL,),
        target=S.PUBLISHED,
        reviewer_emails=(REVIEWER_EMAIL, REVIEWER2_EMAIL),
    ),
    ManuscriptSpec(
        sequence=5,
        title="Optimising Solar-Powered Edge Servers for Rural Connectivity in the Voltaic Basin",
        abstract=(
            "We design a duty-cycling scheme for solar-powered edge servers serving "
            "community Wi-Fi in off-grid communities of the Voltaic Basin, extending "
            "uninterrupted uptime through the dry-season irradiance trough without a "
            "larger battery bank."
        ),
        keywords=("edge computing", "rural connectivity", "renewable energy"),
        corresponding_author_email=AUTHOR_EMAIL,
        co_author_emails=(),
        target=S.PUBLISHED,
        reviewer_emails=(REVIEWER_EMAIL, REVIEWER2_EMAIL),
    ),
    ManuscriptSpec(
        sequence=6,
        title="Named Entity Recognition for Akan-English Code-Switched Text",
        abstract=(
            "We build and release a small annotated corpus of Akan-English code-switched "
            "social media text and fine-tune a multilingual transformer for named entity "
            "recognition, reporting the first published NER baseline for this language "
            "pair."
        ),
        keywords=("named entity recognition", "code-switching", "Akan"),
        corresponding_author_email=AUTHOR2_EMAIL,
        co_author_emails=(AUTHOR_EMAIL,),
        target=S.PUBLISHED,
        reviewer_emails=(REVIEWER_EMAIL, REVIEWER2_EMAIL),
    ),
    ManuscriptSpec(
        sequence=7,
        title=(
            "A Blockchain-Based Framework for Academic Credential Verification "
            "at Ghanaian Universities"
        ),
        abstract=(
            "We present a permissioned-blockchain design for issuing and verifying "
            "degree certificates across multiple Ghanaian universities, and report on a "
            "pilot deployment that cut third-party verification turnaround from weeks to "
            "minutes."
        ),
        keywords=("blockchain", "credential verification", "higher education"),
        corresponding_author_email=AUTHOR_EMAIL,
        co_author_emails=(AUTHOR2_EMAIL,),
        target=S.PUBLISHED,
        reviewer_emails=(REVIEWER_EMAIL, REVIEWER2_EMAIL),
    ),
)

# The fast path's canary: the highest-sequence manuscript this corpus expects to exist.
# Checking only the administrator account (as an earlier version of this script did) would
# make `--if-empty` skip the whole run, including any manuscript this file has since added
# but a prior deploy never got to create — the fast path must track the corpus it guards.
_LAST_SEQUENCE = max(spec.sequence for spec in MANUSCRIPT_SPECS)


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
    """Fast-path check: is there nothing left for this script to do?

    Only used to skip work early under `--if-empty`; the per-record and per-transition
    checks in `_ensure_accounts` and `_advance_manuscript` are what actually make
    re-running safe, so a `False` here never risks a duplicate or a raised guard — it only
    ever does a little more (idempotent) work.
    """
    admin = await uow.accounts.get_by_email(EmailAddress(ADMIN_EMAIL))
    if admin is None or not admin.is_verified or Role.ADMINISTRATOR not in admin.roles:
        return False
    last = await uow.manuscripts.get_by_tracking_code(
        TrackingCode.mint(SEED_TRACKING_YEAR, _LAST_SEQUENCE)
    )
    return last is not None and last.status is S.PUBLISHED


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


def _rationale_for(decision: DecisionType, title: str) -> str:
    if decision is DecisionType.SEND_TO_REVIEW:
        return f"Passes desk screening; sending '{title}' out for double-blind review."
    if decision is DecisionType.REQUEST_REVISION:
        return (
            f"'{title}' needs its methodology section expanded before review; "
            "returned to the author for revision."
        )
    return f"Reviews support acceptance; '{title}' is accepted for publication."


def _review_feedback(reviewer_email: str, title: str) -> tuple[str, str]:
    """A plausible `(recommendation, comments)` pair, varied by which reviewer wrote it."""
    if reviewer_email == REVIEWER_EMAIL:
        return (
            "accept",
            f"The evaluation of '{title}' is thorough and the results are convincing; "
            "I recommend acceptance with only minor copy-editing.",
        )
    return (
        "minor_revision",
        f"'{title}' is a solid contribution; the related-work section should cite two or "
        "three more recent baselines, but the core result stands.",
    )


async def _get_manuscript(uow: SqlAlchemyUnitOfWork, code: TrackingCode) -> Manuscript:
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None:
        raise LookupError(f"manuscript {code.value} was not found after being created")
    return manuscript


async def _advance_manuscript(
    uow: SqlAlchemyUnitOfWork, spec: ManuscriptSpec, ids: dict[str, UserId]
) -> int:
    """Create the manuscript if it does not exist, then resume it towards `spec.target`.

    Every step checks the manuscript's *current* status before acting, so this is safe to
    call on a manuscript a previous run already created (or partly advanced): each already
    completed transition is a no-op, and only the remaining ones run. Returns 1 if the
    manuscript row itself was newly created this call, else 0.
    """
    code = TrackingCode.mint(SEED_TRACKING_YEAR, spec.sequence)
    editor_id = ids[EDITOR_EMAIL]
    eic_id = ids[EIC_EMAIL]
    created = 0

    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None:
        corresponding = ids[spec.corresponding_author_email]
        author_ids = (corresponding, *(ids[email] for email in spec.co_author_emails))
        manuscript = Manuscript(
            id=ManuscriptId(uuid4()),
            tracking_code=code,
            title=spec.title,
            abstract=spec.abstract,
            keywords=spec.keywords,
            author_ids=author_ids,
            corresponding_author_id=corresponding,
        )
        manuscript.submit(actor_id=corresponding, occurred_at=NOW)
        await uow.manuscripts.add(manuscript)
        await uow.commit()
        created = 1
        # Reloaded rather than reused in place: this proves the mapper restores
        # `Manuscript._sequence` correctly from what was just persisted, the same path a
        # manuscript created in an earlier run (and only resumed now) already relies on.
        manuscript = await _get_manuscript(uow, code)

    if spec.target is S.SUBMITTED:
        return created

    if manuscript.status is S.SUBMITTED:
        manuscript.begin_screening(actor_id=editor_id, occurred_at=NOW)
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    if spec.target is S.REVISION_REQUESTED:
        if manuscript.status is S.UNDER_SCREENING:
            manuscript.record_decision(
                decision=DecisionType.REQUEST_REVISION,
                actor_id=editor_id,
                rationale=_rationale_for(DecisionType.REQUEST_REVISION, spec.title),
                occurred_at=NOW,
            )
            await uow.manuscripts.save(manuscript)
            await uow.commit()
        return created

    if manuscript.status is S.UNDER_SCREENING:
        manuscript.record_decision(
            decision=DecisionType.SEND_TO_REVIEW,
            actor_id=editor_id,
            rationale=_rationale_for(DecisionType.SEND_TO_REVIEW, spec.title),
            occurred_at=NOW,
        )
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    await _ensure_reviewers_assigned(uow, manuscript.id, spec.reviewer_emails, ids)

    if spec.target is S.UNDER_REVIEW:
        first_reviewer_id = ids[spec.reviewer_emails[0]]
        already_submitted = any(
            record.reviewer_id == first_reviewer_id and record.status == "submitted"
            for record in await uow.assignments.list_for_manuscript(manuscript.id)
        )
        if manuscript.status is S.UNDER_REVIEW and not already_submitted:
            await _submit_one_review(uow, manuscript, spec.reviewer_emails[0], spec.title, ids)
        return created

    if manuscript.status is S.UNDER_REVIEW:
        submitted = {
            record.reviewer_id
            for record in await uow.assignments.list_for_manuscript(manuscript.id)
            if record.status == "submitted"
        }
        for reviewer_email in spec.reviewer_emails:
            if ids[reviewer_email] in submitted:
                continue
            await _submit_one_review(uow, manuscript, reviewer_email, spec.title, ids)
            if manuscript.status is not S.UNDER_REVIEW:
                break

    if manuscript.status is S.REVIEWS_COMPLETE:
        manuscript.record_decision(
            decision=DecisionType.ACCEPT,
            actor_id=eic_id,
            rationale=_rationale_for(DecisionType.ACCEPT, spec.title),
            occurred_at=NOW,
        )
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    if manuscript.status is S.ACCEPTED:
        manuscript.schedule(issue_id=DEMO_ISSUE_ID, actor_id=eic_id, occurred_at=NOW)
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    if manuscript.status is S.SCHEDULED:
        manuscript.publish(actor_id=eic_id, occurred_at=NOW)
        await uow.manuscripts.save(manuscript)
        await uow.commit()

    return created


async def _ensure_reviewers_assigned(
    uow: SqlAlchemyUnitOfWork,
    manuscript_id: ManuscriptId,
    reviewer_emails: Sequence[str],
    ids: dict[str, UserId],
) -> None:
    if not reviewer_emails:
        return
    already = {
        record.reviewer_id for record in await uow.assignments.list_for_manuscript(manuscript_id)
    }
    assigned_any = False
    for reviewer_email in reviewer_emails:
        reviewer_id = ids[reviewer_email]
        if reviewer_id in already:
            continue
        await uow.assignments.assign(manuscript_id, reviewer_id, occurred_at=NOW)
        assigned_any = True
    if assigned_any:
        await uow.commit()


async def _submit_one_review(
    uow: SqlAlchemyUnitOfWork,
    manuscript: Manuscript,
    reviewer_email: str,
    title: str,
    ids: dict[str, UserId],
) -> None:
    reviewer_id = ids[reviewer_email]
    manuscript.record_review(reviewer_id=reviewer_id, occurred_at=NOW)
    await uow.manuscripts.save(manuscript)
    recommendation, comments = _review_feedback(reviewer_email, title)
    await uow.assignments.mark_submitted(
        manuscript.id,
        reviewer_id,
        recommendation=recommendation,
        comments=comments,
        occurred_at=NOW,
    )
    await uow.commit()


async def _ensure_demo_corpus(uow: SqlAlchemyUnitOfWork, ids: dict[str, UserId]) -> int:
    """Create or resume every demo manuscript, returning how many were newly created."""
    created = 0
    for spec in MANUSCRIPT_SPECS:
        created += await _advance_manuscript(uow, spec, ids)
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
            await uow.commit()
            created = await _ensure_demo_corpus(uow, ids)
            print(
                f"Ensured {len(JUDGE_ACCOUNTS)} judge account(s); "
                f"created {created} new demo manuscript(s) "
                f"(of {len(MANUSCRIPT_SPECS)} in the target corpus)."
            )
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--if-empty",
        action="store_true",
        default=False,
        help="Skip all work if the administrator account and full corpus already exist.",
    )
    args = parser.parse_args()
    asyncio.run(run(only_if_empty=args.if_empty))


if __name__ == "__main__":
    main()
