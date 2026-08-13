"""A top-to-bottom line flow with automatic page breaks, over `pdf_text`'s primitives.

`pdf_text.py` positions every line absolutely; this class is for documents whose length
is data-dependent (the certificate's review count), where the caller wants to append
lines and let pagination happen at the bottom margin.
"""

from ugjcs.infrastructure.storage.pdf_text import MARGIN, PAGE_HEIGHT, Line, wrap


class LineFlow:
    """Accumulate lines top to bottom, breaking to a new page at the bottom margin."""

    def __init__(self) -> None:
        self._pages: list[list[Line]] = []
        self._lines: list[Line] = []
        self._y = PAGE_HEIGHT - MARGIN

    def line(self, font_name: str, size: float, text: str, *, leading: float) -> None:
        if self._y < MARGIN:
            self._pages.append(self._lines)
            self._lines = []
            self._y = PAGE_HEIGHT - MARGIN
        self._lines.append((font_name, size, self._y, text))
        self._y -= leading

    def wrapped(
        self, font_name: str, size: float, text: str, *, width: int, leading: float
    ) -> None:
        for piece in wrap(text, width):
            self.line(font_name, size, piece, leading=leading)

    def gap(self, amount: float) -> None:
        self._y -= amount

    def pages(self) -> list[list[Line]]:
        return [*self._pages, self._lines] if self._lines else list(self._pages)
