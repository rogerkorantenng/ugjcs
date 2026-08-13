"""The administrator's console: accounts, roles, capacity, activation.

Every route is gated by `Action.MANAGE_USERS`, which `_ROLE_GRANTS` gives to
`Role.ADMINISTRATOR` alone. Two deliberate refusals shape this API:

- The administrator role itself can be neither granted nor revoked here. Administrator
  appointments are an out-of-band, deployment-level act (the seed script); an admin
  console that could mint admins would make one compromised admin account into a
  self-replicating one.
- An administrator cannot deactivate their own account: the last admin locking
  themselves out is unrecoverable from inside the application, and the cheap guard is
  refusing self-deactivation outright rather than counting remaining admins.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ugjcs.api.deps import require as require_action
from ugjcs.api.schemas_wave2 import (
    ActiveChangeRequest,
    AdminAccountOut,
    CapacityChangeRequest,
    RoleChangeRequest,
)
from ugjcs.api.wiring import UowDep
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.account import Account
from ugjcs.domain.enums import Role
from ugjcs.domain.ids import UserId
from ugjcs.domain.policies import Action, Actor

router = APIRouter()

# Module-level alias for the same ruff-B008 reason as every other router's gates.
AdminDep = Annotated[Actor, Depends(require_action(Action.MANAGE_USERS))]


@router.get("/accounts", response_model=list[AdminAccountOut])
async def list_accounts(actor: AdminDep, uow: UowDep) -> list[AdminAccountOut]:
    """The full roster, inactive and unverified accounts included — they are the
    console's work queue, not noise to filter (see `AccountRepository.list_all`)."""
    return [AdminAccountOut.from_domain(account) for account in await uow.accounts.list_all()]


@router.post("/accounts/{account_id}/roles", response_model=AdminAccountOut)
async def change_role(
    account_id: UUID, body: RoleChangeRequest, actor: AdminDep, uow: UowDep
) -> AdminAccountOut:
    """Grant or revoke one non-administrator role.

    Grant is idempotent (`Account.grant` is a set-add); revoking a role the account
    does not hold raises `AccountError`, which the error handler maps to 400 — an
    honest "that revocation describes a state that does not exist"."""
    if body.role is Role.ADMINISTRATOR:
        raise HTTPException(
            status_code=403, detail="the administrator role cannot be changed through this API"
        )
    account = await _account_or_404(uow, account_id)
    if body.grant:
        account.grant(body.role)
    else:
        account.revoke(body.role)
    await uow.accounts.save(account)
    await uow.commit()
    return AdminAccountOut.from_domain(account)


@router.post("/accounts/{account_id}/capacity", response_model=AdminAccountOut)
async def change_capacity(
    account_id: UUID, body: CapacityChangeRequest, actor: AdminDep, uow: UowDep
) -> AdminAccountOut:
    """Set how many concurrent review assignments this account may carry (1..10 —
    enforced by `CapacityChangeRequest`, so an out-of-range value 422s before here)."""
    account = await _account_or_404(uow, account_id)
    account.reviewer_capacity = body.reviewer_capacity
    await uow.accounts.save(account)
    await uow.commit()
    return AdminAccountOut.from_domain(account)


@router.post("/accounts/{account_id}/active", response_model=AdminAccountOut)
async def change_active(
    account_id: UUID, body: ActiveChangeRequest, actor: AdminDep, uow: UowDep
) -> AdminAccountOut:
    if account_id == UUID(str(actor.id)) and not body.is_active:
        raise HTTPException(
            status_code=409, detail="an administrator cannot deactivate their own account"
        )
    account = await _account_or_404(uow, account_id)
    if body.is_active:
        account.reactivate()
    else:
        account.deactivate()
    await uow.accounts.save(account)
    await uow.commit()
    return AdminAccountOut.from_domain(account)


async def _account_or_404(uow: UnitOfWork, account_id: UUID) -> Account:
    account = await uow.accounts.get(UserId(account_id))
    if account is None:
        raise HTTPException(status_code=404, detail="account not found")
    return account
