"""The public archive. No authentication anywhere in this file, by design."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ugjcs.api.routers.manuscripts import _presigned
from ugjcs.api.schemas import ArchivePaperOut, DocumentUrlOut
from ugjcs.api.wiring import DocumentStoreDep, UowDep
from ugjcs.application.ports import UnitOfWork
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.ids import TrackingCode
from ugjcs.domain.manuscript import Manuscript

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
    manuscript = await _published_or_404(uow, tracking_code)
    return await ArchivePaperOut.from_domain(manuscript, uow.accounts)


@router.get("/{tracking_code}/document", response_model=DocumentUrlOut)
async def download_published_document(
    tracking_code: str, uow: UowDep, documents: DocumentStoreDep
) -> DocumentUrlOut:
    """FR-18: a reader downloads a published paper's PDF, unauthenticated. Gated on
    `manuscript.status is PUBLISHED` the same way `retrieve_published` is — a manuscript
    still anywhere in the workflow (even `SCHEDULED`, one step short of published) is
    never reachable here, so this route cannot leak a paper still under review.
    """
    manuscript = await _published_or_404(uow, tracking_code)
    if manuscript.original_document_key is None:
        raise HTTPException(status_code=404, detail="no document has been attached")
    return await _presigned(documents, manuscript.original_document_key)


async def _published_or_404(uow: UnitOfWork, tracking_code: str) -> Manuscript:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="paper not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None or manuscript.status is not S.PUBLISHED:
        raise HTTPException(status_code=404, detail="paper not found")
    return manuscript
