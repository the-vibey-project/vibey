# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading a chapter's content out of a built documentation page."""

from __future__ import annotations

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
