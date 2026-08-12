"""The public archive. No authentication anywhere in this file, by design."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ugjcs.api.schemas import ArchivePaperOut
from ugjcs.api.wiring import UowDep
from ugjcs.domain.ids import TrackingCode

router = APIRouter()

SearchQuery = Annotated[str, Query(min_length=1)]


@router.get("", response_model=list[ArchivePaperOut])
async def list_published(uow: UowDep) -> list[ArchivePaperOut]:
    manuscripts = await uow.manuscripts.list_published()
    return [await ArchivePaperOut.from_domain(m, uow.accounts) for m in manuscripts]


@router.get("/search", response_model=list[ArchivePaperOut])
async def search(q: SearchQuery, uow: UowDep) -> list[ArchivePaperOut]:
    manuscripts = await uow.manuscripts.search_published(q)
    return [await ArchivePaperOut.from_domain(m, uow.accounts) for m in manuscripts]


@router.get("/{tracking_code}", response_model=ArchivePaperOut)
async def retrieve_published(tracking_code: str, uow: UowDep) -> ArchivePaperOut:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="paper not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None or manuscript.status.value != "published":
        raise HTTPException(status_code=404, detail="paper not found")
    return await ArchivePaperOut.from_domain(manuscript, uow.accounts)
