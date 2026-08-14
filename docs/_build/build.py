"""Rebuild docs/html/ from docs/*.md.

Mermaid fences are replaced with SVG figures rendered by a previous run of the original
build script and cached alongside this file. Their sources are verified unchanged before
reuse, so this produces byte-identical diagrams without needing headless Chrome.
Everything else goes through pandoc with the same stylesheet, page chrome and titles the
existing pages already use.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / "docs"
OUT = DOCS / "html"
HERE = Path(__file__).parent

MERMAID = re.compile(r"```mermaid\n(.*?)```", re.S)

TITLES = {
    "01-project-documentation.md": "01 · Project Documentation",
    "02-srs.md": "02 · Software Requirements Specification",
    "03-effort-estimation.md": "03 · Effort Estimation (UCP + COCOMO II)",
    "04-technical-debt-register.md": "04 · Technical Debt Register",
    "05-api-contract.md": "05 · API Contract",
    "06-testing-report.md": "06 · Testing Report",
    "07-user-manual.md": "07 · User Manual",
    "08-qa-report.md": "08 · QA Report",
}

EYEBROW = "Science and Development Journal (SDJ) — Editorial Portal · Submission Documentation"
FOOTER = (
    '<footer class="site">SDJ Editorial Portal — Advanced Software Engineering '
    "final project · Roger Koranteng Obeng · 22424140</footer>"
)

CSS = (HERE / "custom.css").read_text()
BASE_CSS = (HERE / "pandoc-base.css").read_text()


def header_html(title: str) -> str:
    return (
        '<header class="site">\n'
        '  <div class="inner">\n'
        f'    <div class="eyebrow">{EYEBROW}</div>\n'
        f'    <div class="title">{title}</div>\n'
        "  </div>\n"
        "</header>\n"
        "<main>\n"
        '<nav class="docnav"><a href="index.html">← All documents</a></nav>'
    )


def footer_html() -> str:
    return "</main>\n" + FOOTER


META_LINE = re.compile(r"^\*\*(?P<key>[^*]+?):?\*\*\s*(?P<val>.*)$")


def metadata_panel(text: str) -> str:
    """Turn the run of `**Key:** value` lines under the H1 into a definition list.

    Left as markdown they collapse into one paragraph, because a single newline is a
    soft break in GFM. Enabling hard line breaks document-wide would instead break every
    wrapped prose line, so the block is lifted out here and emitted as raw HTML.
    """
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
    if start is None:
        return text

    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    first = i
    rows: list[tuple[str, str]] = []
    while i < len(lines) and lines[i].strip():
        m = META_LINE.match(lines[i].strip())
        if m and m.group("val").strip():
            rows.append((m.group("key").strip(), m.group("val").strip()))
            i += 1
            continue
        # A soft-wrapped continuation of the value above, not a new field. Anything
        # else (a heading, a rule, a "**Naming.** …" paragraph) ends the block.
        if rows and not lines[i].lstrip().startswith(("**", "#", "-", "|", ">")):
            key, val = rows[-1]
            rows[-1] = (key, f"{val} {lines[i].strip()}")
            i += 1
            continue
        break

    if len(rows) < 3:
        return text

    items = "\n".join(
        f"  <dt>{k}</dt>\n  <dd>{md_inline(v)}</dd>" for k, v in rows
    )
    panel = f'<dl class="docmeta">\n{items}\n</dl>'
    return "\n".join(lines[:first] + [panel] + lines[i:])


def md_inline(s: str) -> str:
    """Inline code spans and bold, the only markup these metadata values carry."""
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


CELL = re.compile(r"<(?:th|td)\b[^>]*>(.*?)</(?:th|td)>", re.S)
ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
TAG = re.compile(r"<[^>]+>")


def column_widths(table_html: str) -> list[float] | None:
    """Proportional column widths, as percentages, from the text each column carries.

    With `table-layout: fixed` (which print needs, so a wide matrix cannot overflow the
    page and lose its last column) the browser would otherwise divide the width equally,
    giving an "FR-01" column the same room as a column of test names. Widths are damped
    with a square root: a column holding four times the text gets twice the width, not
    four times, so the widest column cannot starve the rest.
    """
    rows = ROW.findall(table_html)
    if len(rows) < 2:
        return None
    lengths: list[list[int]] = []
    for row in rows:
        cells = [len(TAG.sub("", c).strip()) for c in CELL.findall(row)]
        if cells:
            lengths.append(cells)
    if not lengths:
        return None

    columns = max(len(r) for r in lengths)
    if columns < 2:
        return None
    means = []
    for i in range(columns):
        vals = [r[i] for r in lengths if len(r) > i]
        means.append(sum(vals) / len(vals) if vals else 1.0)

    damped = [max(m, 1.0) ** 0.5 for m in means]
    total = sum(damped)
    # A floor keeps a genuinely tiny column (an FR id) readable rather than hair-thin.
    pct = [max(9.0, 100 * d / total) for d in damped]
    scale = 100 / sum(pct)
    return [round(p * scale, 2) for p in pct]


def wrap_tables(html: str) -> str:
    """Add a scroll container (for screen) and a computed colgroup (for print)."""

    def repl(match: re.Match[str]) -> str:
        table = match.group(0)
        widths = column_widths(table)
        if widths:
            cols = "".join(f'<col style="width:{w}%" />' for w in widths)
            table = table.replace("<table>", f"<table><colgroup>{cols}</colgroup>", 1)
        return f'<div class="tablewrap">{table}</div>'

    return re.sub(r"<table>.*?</table>", repl, html, flags=re.S)


def substitute_diagrams(text: str, stem: str) -> str:
    """Swap each mermaid fence for its cached, pre-rendered figure."""
    counter = 0

    def repl(_match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        cached = HERE / f"{stem}-{counter}.svg.html"
        if not cached.exists():
            raise SystemExit(f"missing cached diagram {cached.name}")
        return cached.read_text()

    return MERMAID.sub(repl, text)


def build(md_path: Path) -> None:
    title = TITLES[md_path.name]
    text = substitute_diagrams(md_path.read_text(), md_path.stem)
    text = metadata_panel(text)

    prepared = HERE / f"prepared-{md_path.name}"
    prepared.write_text(text)
    (HERE / "head.html").write_text(f"<style>{BASE_CSS}</style>\n<style>{CSS}</style>")
    (HERE / "before.html").write_text(header_html(title))
    (HERE / "after.html").write_text(footer_html())

    out = OUT / (md_path.stem + ".html")
    subprocess.run(
        [
            # A custom template, because pandoc's default one ships a stylesheet
            # containing `body { max-width: 36em }` that loads after --include-in-header
            # and silently squeezes every printed page into half its width.
            "pandoc", str(prepared),
            "-f", "gfm+raw_html", "-t", "html5", "--standalone",
            "--template", str(HERE / "template.html"),
            "-V", f"pagetitle={title}",
            "--include-in-header", str(HERE / "head.html"),
            "--include-before-body", str(HERE / "before.html"),
            "--include-after-body", str(HERE / "after.html"),
            "-o", str(out),
        ],
        check=True,
    )
    out.write_text(wrap_tables(out.read_text()))
    print(f"built {out.name}")


def index_page() -> None:
    items = "\n".join(
        f'    <li><a href="{Path(name).stem}.html">{title}</a></li>'
        for name, title in TITLES.items()
    )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>SDJ Editorial Portal — Documentation</title>
<style>{CSS}</style>
<style>
  ul.doclist {{ list-style:none; padding:0; }}
  ul.doclist li {{ border-bottom:1px solid var(--rule); }}
  ul.doclist li:last-child {{ border-bottom:0; }}
  ul.doclist a {{ display:block; padding:.85rem .2rem; font-weight:600; text-decoration:none; }}
  ul.doclist a:hover {{ color:var(--blue); }}
</style>
</head>
<body>
<header class="site">
  <div class="inner">
    <div class="eyebrow">{EYEBROW}</div>
    <div class="title">Submission documentation</div>
  </div>
</header>
<main>
  <p>Eight documents, in the order they are meant to be read.</p>
  <ul class="doclist">
{items}
  </ul>
</main>
{FOOTER}
</body>
</html>
"""
    (OUT / "index.html").write_text(html)
    print("built index.html")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name in TITLES:
        build(DOCS / name)
    index_page()
    sys.exit(0)
