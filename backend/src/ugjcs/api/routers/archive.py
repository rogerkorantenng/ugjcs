"""The public archive. No authentication anywhere in this file, by design."""

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ugjcs.api.routers.manuscripts import _presigned
from ugjcs.api.schemas import ArchivePaperOut, DocumentUrlOut
from ugjcs.api.schemas_scholarly import ProvenanceEventOut, ProvenanceOut
from ugjcs.api.schemas_wave2 import ArchiveSearchResultOut
from ugjcs.api.wiring import DocumentStoreDep, UowDep
from ugjcs.application.ports import UnitOfWork
from ugjcs.application.scholarly import bibtex_citation, ris_citation
from ugjcs.domain.enums import ManuscriptStatus as S
from ugjcs.domain.hashchain import GENESIS_HASH, ChainBrokenError, verify
from ugjcs.domain.ids import TrackingCode
from ugjcs.domain.manuscript import Manuscript

router = APIRouter()

SearchQuery = Annotated[str, Query(min_length=1)]
# Aliased because a `format` parameter would shadow the builtin (ruff A002); an unknown
# value fails the `Literal` and FastAPI returns 422, exactly the contract.
CitationFormat = Annotated[Literal["bibtex", "ris"], Query(alias="format")]


@router.get("", response_model=list[ArchivePaperOut])
async def list_published(uow: UowDep) -> list[ArchivePaperOut]:
    manuscripts = await uow.manuscripts.list_published()
    return [await ArchivePaperOut.from_domain(m, uow.accounts) for m in manuscripts]


@router.get("/search", response_model=list[ArchiveSearchResultOut])
async def search(q: SearchQuery, uow: UowDep) -> list[ArchiveSearchResultOut]:
    """Title, abstract and keyword matching as before, now unioned with full-text
    search over the published PDFs' extracted body text. A result whose match came
    from the body carries a `snippet` of the surrounding context; a metadata match
    carries `snippet: null` — see `PublishedSearchHit` for the contract."""
    hits = await uow.manuscripts.search_published_with_snippets(q)
    return [await ArchiveSearchResultOut.from_hit(hit, uow.accounts) for hit in hits]


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


@router.get("/{tracking_code}/provenance", response_model=ProvenanceOut)
async def provenance(tracking_code: str, uow: UowDep) -> ProvenanceOut:
    """Recompute the paper's editorial event hash chain and publish a summary of it.
    Published manuscripts only — anything still in the workflow is a 404 here, the same
    gate every other `/archive` route applies.

    `intact` means exactly what `ugjcs.domain.hashchain.verify` proves and no more: every
    stored link reconciles against a recomputation from the genesis hash, so no interior
    event was altered, reordered or removed. Stated plainly, as that module's docstring
    does, what `intact` does NOT prove: it cannot detect truncation of the tail (any
    prefix of a valid chain is itself a valid chain), a forged event appended through the
    normal path, or a wholly fabricated history rebuilt from genesis — those need an
    externally published checkpoint, out of scope per the technical-debt register.
    Each event exposes only its type, timestamp and an 8-character hash prefix — never
    the payload or actor, because payloads can reference reviewer identifiers."""
    manuscript = await _published_or_404(uow, tracking_code)
    chain = await uow.manuscripts.chain_for(manuscript.id)
    try:
        verify(chain)
        intact = True
    except ChainBrokenError:
        intact = False
    return ProvenanceOut(
        tracking_code=manuscript.tracking_code.value,
        intact=intact,
        head_hash=chain[-1].event_hash if chain else GENESIS_HASH,
        events=[
            ProvenanceEventOut(
                sequence=link.event.sequence,
                event_type=link.event.event_type.value,
                occurred_at=link.event.occurred_at,
                hash_prefix=link.event_hash[:8],
            )
            for link in chain
        ],
    )


@router.get("/{tracking_code}/citation", response_class=PlainTextResponse)
async def citation(
    tracking_code: str, citation_format: CitationFormat, uow: UowDep
) -> PlainTextResponse:
    """A ready-to-paste citation for a published paper, as BibTeX or RIS plain text.
    Carries the DOI-shaped identifier (`ArchivePaperOut.doi` — fake registrant
    `10.55555`, unregistered by documented scope) and the portal URL."""
    manuscript = await _published_or_404(uow, tracking_code)
    paper = await ArchivePaperOut.from_domain(manuscript, uow.accounts)
    render = bibtex_citation if citation_format == "bibtex" else ris_citation
    text = render(tracking_code=paper.tracking_code, title=paper.title, authors=paper.author_names)
    return PlainTextResponse(content=text)


async def _published_or_404(uow: UnitOfWork, tracking_code: str) -> Manuscript:
    try:
        code = TrackingCode.parse(tracking_code)
    except ValueError as error:
        raise HTTPException(status_code=404, detail="paper not found") from error
    manuscript = await uow.manuscripts.get_by_tracking_code(code)
    if manuscript is None or manuscript.status is not S.PUBLISHED:
        raise HTTPException(status_code=404, detail="paper not found")
    return manuscript
