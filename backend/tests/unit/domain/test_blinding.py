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


def test_blinded_view_preserves_reviewable_content() -> None:
    blinded = blind(manuscript())
    assert blinded.title == "Low-Bandwidth Telemedicine Protocols"
    assert blinded.keywords == ("telemedicine", "protocols")


def test_blinded_view_has_no_author_fields_in_its_type() -> None:
    field_names = {field.name for field in dataclasses.fields(BlindedManuscript)}
    assert not any("author" in name for name in field_names)


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
