import dataclasses
from uuid import uuid4

from ugjcs.domain.blinding import BlindedManuscript, blind
from ugjcs.domain.ids import ManuscriptId, TrackingCode, UserId
from ugjcs.domain.manuscript import Manuscript

SENTINEL_AUTHOR = UserId(uuid4())


def manuscript() -> Manuscript:
    return Manuscript(
        id=ManuscriptId(uuid4()),
        tracking_code=TrackingCode.mint(2026, 9),
        title="Low-Bandwidth Telemedicine Protocols",
        abstract="A protocol for clinical consultation over intermittent links.",
        keywords=("telemedicine", "protocols"),
        author_ids=(SENTINEL_AUTHOR,),
        corresponding_author_id=SENTINEL_AUTHOR,
    )


def test_blinded_view_preserves_every_reviewable_field() -> None:
    blinded = blind(manuscript())
    assert blinded.tracking_code == "UGJCS-2026-0009"
    assert blinded.title == "Low-Bandwidth Telemedicine Protocols"
    assert blinded.abstract == "A protocol for clinical consultation over intermittent links."
    assert blinded.keywords == ("telemedicine", "protocols")
    assert blinded.version == 1
    assert blinded.status == "draft"


def test_blinded_view_exposes_exactly_the_permitted_fields() -> None:
    """Any field added to BlindedManuscript must be a deliberate decision.

    A substring check for "author" would not catch `affiliation`, `submitter_id` or
    `corresponding_email`. Pinning the exact set makes this test fail whenever the type
    grows, so an addition has to be justified rather than merely compile.
    """
    assert {field.name for field in dataclasses.fields(BlindedManuscript)} == {
        "tracking_code",
        "title",
        "abstract",
        "keywords",
        "version",
        "status",
    }


def test_blinded_view_never_serialises_an_author_identifier() -> None:
    blinded = blind(manuscript())
    serialised = repr(dataclasses.asdict(blinded))
    assert str(SENTINEL_AUTHOR) not in serialised


def test_blinded_view_is_immutable() -> None:
    blinded = blind(manuscript())
    try:
        blinded.title = "changed"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("BlindedManuscript should be immutable")
