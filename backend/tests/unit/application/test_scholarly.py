"""The pure scholarly-record derivations: fake DOI, keys, and citation bodies."""

from ugjcs.application.scholarly import (
    bibtex_citation,
    citation_key,
    fake_doi,
    paper_url,
    publication_year,
    ris_citation,
)


def test_the_fake_doi_is_lowercase_and_dot_separated_under_the_fake_prefix() -> None:
    assert fake_doi("SDJ-2026-0004") == "10.55555/sdj.2026.0004"


def test_the_citation_key_is_bibtex_safe() -> None:
    assert citation_key("SDJ-2026-0004") == "sdj_2026_0004"


def test_the_publication_year_comes_from_the_tracking_code() -> None:
    assert publication_year("SDJ-2026-0004") == 2026


def test_the_paper_url_points_at_the_portal() -> None:
    assert paper_url("SDJ-2026-0004") == "https://ugjcs-frontend.vercel.app/papers/SDJ-2026-0004"


def test_bibtex_joins_authors_with_and_and_closes_the_entry() -> None:
    entry = bibtex_citation(
        tracking_code="SDJ-2026-0004",
        title="Fair Scheduling",
        authors=["Ama Serwaa", "Kofi Mensah"],
    )
    assert entry.startswith("@article{sdj_2026_0004,")
    assert "{Ama Serwaa and Kofi Mensah}" in entry
    assert entry.rstrip().endswith("}")


def test_ris_opens_with_ty_jour_and_ends_with_er() -> None:
    record = ris_citation(
        tracking_code="SDJ-2026-0004",
        title="Fair Scheduling",
        authors=["Ama Serwaa"],
    )
    lines = record.splitlines()
    assert lines[0] == "TY  - JOUR"
    assert lines[-1] == "ER  -"
    assert "AU  - Ama Serwaa" in lines
