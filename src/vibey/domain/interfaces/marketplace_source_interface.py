# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over which marketplace sources and refs vibey fetches (SP-LOOPS Task 7).

Implemented by `domain/marketplace_source.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.marketplace_source import MarketplaceSource


@runtime_checkable
class MarketplaceSourceRuleInterface(Protocol):
    def classify(self, source: str) -> MarketplaceSource:
        """`source` as git (an `https://`, `ssh://` or `git://` URL with a plain host and no
        credentials, or `user@host:path`) or local (an absolute folder path, copied without
        git). Raises `MarketplaceSourceError` naming why for anything else: a transport helper
        (`::`), `file://`, `http://`, a relative or `~` path, `..`, a leading `-`, whitespace or
        control characters."""
        ...

    def check_ref(self, ref: str) -> str:
        """`ref` unchanged when it is a plain branch, tag or commit name that git cannot read as
        an option or a refspec; else `MarketplaceSourceError`."""
        ...

    def is_commit(self, ref: str) -> bool:
        """Whether `ref` is a full commit id (40 or 64 lower-case hex digits), which the fetched
        commit must then equal."""
        ...
