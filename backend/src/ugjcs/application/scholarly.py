"""Scholarly-record derivations: the DOI-shaped identifier and citation exports.

The identifier is DOI-*shaped* but NOT registered — SRS §4.2 and the technical-debt
register are explicit that real Crossref DOI registration is out of scope, so the
registrant prefix `10.55555` below is a documented fake: resolving one of these at
doi.org fails by design. Everything here is derived from the tracking code and the
paper's public fields; nothing is stored, so nothing can drift.
"""

from collections.abc import Sequence

JOURNAL_NAME = "Science and Development Journal"
FAKE_DOI_PREFIX = "10.55555"
"""A fake registrant prefix. Real prefixes are allocated by a DOI registration agency;
this one is not, matching the SRS's "DOI-shaped but unregistered" scope decision."""
PORTAL_BASE_URL = "https://ugjcs-frontend.vercel.app"
"""The deployed portal (SRS §1) — public papers live under `/papers/{tracking_code}`."""


def fake_doi(tracking_code: str) -> str:
    """`SDJ-2026-0004` -> `10.55555/sdj.2026.0004` (lowercase, dot-separated)."""
    return f"{FAKE_DOI_PREFIX}/{tracking_code.lower().replace('-', '.')}"


def citation_key(tracking_code: str) -> str:
    """`SDJ-2026-0004` -> `sdj_2026_0004`, a BibTeX-safe key."""
    return tracking_code.lower().replace("-", "_")


def publication_year(tracking_code: str) -> int:
    """The year segment of the tracking code — the only year the domain records."""
    return int(tracking_code.split("-")[1])


def paper_url(tracking_code: str) -> str:
    return f"{PORTAL_BASE_URL}/papers/{tracking_code}"


def bibtex_citation(*, tracking_code: str, title: str, authors: Sequence[str]) -> str:
    """A well-formed `@article` entry; authors joined with `" and "` per BibTeX."""
    return "\n".join(
        (
            f"@article{{{citation_key(tracking_code)},",
            f"  author  = {{{' and '.join(authors)}}},",
            f"  title   = {{{title}}},",
            f"  journal = {{{JOURNAL_NAME}}},",
            f"  year    = {{{publication_year(tracking_code)}}},",
            f"  doi     = {{{fake_doi(tracking_code)}}},",
            f"  url     = {{{paper_url(tracking_code)}}},",
            "}",
            "",
        )
    )


def ris_citation(*, tracking_code: str, title: str, authors: Sequence[str]) -> str:
    """An RIS journal-article record: `TY  - JOUR` through `ER  -`, one tag per line."""
    rows = (
        "TY  - JOUR",
        *(f"AU  - {author}" for author in authors),
        f"TI  - {title}",
        f"JO  - {JOURNAL_NAME}",
        f"PY  - {publication_year(tracking_code)}",
        f"DO  - {fake_doi(tracking_code)}",
        f"UR  - {paper_url(tracking_code)}",
        "ER  -",
        "",
    )
    return "\n".join(rows)
