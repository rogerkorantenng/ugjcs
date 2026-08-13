"""Finding another account without asking them for their raw database UUID.

This is the whole reason FR-08/FR-13's forms (co-author ids on submission, reviewer id
on assignment) were unusable: nobody knows a colleague's UUID by heart, and there was no
way to find one from the frontend alone.
"""

from fastapi import APIRouter, HTTPException

from ugjcs.api.deps import ActorDep
from ugjcs.api.schemas import PersonOut
from ugjcs.api.wiring import UowDep
from ugjcs.domain.account import EmailAddress

router = APIRouter()


@router.get("/lookup", response_model=PersonOut)
async def lookup(email: str, actor: ActorDep, uow: UowDep) -> PersonOut:
    """Exact, case-insensitive email match only — any authenticated user may call this.

    Deliberately not a search: a partial-match query across all accounts would turn this
    into a directory anyone with a login could enumerate, and an author genuinely knows
    their co-author's email address, so exact lookup is all FR-08/FR-13 need. The email
    is never echoed back — see `PersonOut` — because the caller already supplied it.

    Rate limiting: this endpoint is enumerable by brute force over guessed addresses (a
    caller can distinguish "account exists" from "no account" one exact address at a
    time). It must sit behind a rate limiter before real users are admitted — recorded
    as TD-15 (Critical) in `docs/04-technical-debt-register.md`. No limiter exists yet.
    """
    try:
        normalised = EmailAddress(email)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="no account for this email") from error
    account = await uow.accounts.get_by_email(normalised)
    if account is None:
        raise HTTPException(status_code=404, detail="no account for this email")
    return PersonOut.from_domain(account)
