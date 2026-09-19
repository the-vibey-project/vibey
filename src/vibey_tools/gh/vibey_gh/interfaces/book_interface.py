# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for turning a built documentation site into a book."""

from __future__ import annotations

import datetime
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class MainExtractorInterface(Protocol):
    """Walks a rendered page and collects the content element's subtree.

    A parser rather than a pattern, because the content element nests arbitrarily and no
    regular expression balances that. It decides nothing about what survives or how it is
    written down -- that is the sanitizer's judgement, injected -- so the seam it offers a
    caller is only: push markup in, read the collected pieces out.
    """

    out: list[str]

    def feed(self, data: str) -> None:
        """Push a page's markup through the walk, appending what survives to `out`."""

    def close(self) -> None:
        """Finish the walk, closing whatever the document left open.

        Declared rather than left to the implementation: `out` is only well-formed once
        the caller has said no more markup is coming. HTML permits an end tag to be
        omitted, so until then the collected pieces may have elements still open -- and
        an unbalanced fragment fails the XHTML parse for the whole package, not just for
        the chapter it came from.
        """


@runtime_checkable
class BookChapterInterface(Protocol):
    """One chapter as every renderer reads it: a plain-text title and where it sits.

    Read-only by declaration. A chapter is identified by its slug in the EPUB manifest,
    the print interior's anchors and its named page, so nothing downstream may rename
    one after the nav has been read.
    """

    @property
    def title(self) -> str:
        """The nav title as plain text -- quotes and markdown code spans already gone."""

    @property
    def sections(self) -> tuple[str, ...]:
        """The nav section headings enclosing this chapter, outermost first."""

    @property
    def slug(self) -> str:
        """A stable identifier derived from the source path, safe as a file name or id."""


@runtime_checkable
class NavReaderInterface(Protocol):
    """Reads the ordered chapter list, section headings included, out of a site's nav."""

    def read(self, config_text: str) -> Sequence[BookChapterInterface]:
        """Every chapter in nav order. Raises when the nav names none."""


@runtime_checkable
class TableOfContentsInterface(Protocol):
    """The chapters grouped the way the nav groups them."""

    def ordered_list(self, link: Callable[[BookChapterInterface], str]) -> str:
        """Nested <ol>s: each section a <span> heading over the list of what it holds.

        `link` turns a chapter into the href its entry points at, so one table serves
        both the EPUB navigation document and the print interior.
        """


@runtime_checkable
class PrintInteriorInterface(Protocol):
    """Renders the print-ready HTML a headless browser prints as the paperback interior."""

    def css(self) -> str:
        """The interior's stylesheet: trim, mirrored margins, folios and typography."""

    def render(
        self,
        meta: Mapping[str, str],
        chapters: Sequence[BookChapterInterface],
        bodies: Mapping[str, str],
        year: int,
    ) -> str:
        """The whole interior as one HTML document: front matter, contents, chapters.

        `bodies` maps each chapter's slug to its extracted content.
        """


@runtime_checkable
class EpubPackageInterface(Protocol):
    """Writes the EPUB 3 container a reader, and KDP's ingestion, will open."""

    def identifier(self, meta: Mapping[str, str]) -> str:
        """The publication's unique identifier -- the same for the same book, every build."""

    def write(
        self,
        path: Path,
        meta: Mapping[str, str],
        chapters: Sequence[BookChapterInterface],
        bodies: Mapping[str, str],
        now: datetime.datetime,
    ) -> None:
        """Write the package to `path`. `now` stamps `dcterms:modified`."""
