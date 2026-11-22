# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the hub's guarded fetch of one page.

Mirrors `vibey/infrastructure/web/guarded_fetch.py` (ADR-0016). Interfaces declare; they never
consume. It fills the application's `WebFetchPortInterface`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import WebPage
    from vibey.domain.web_tools import WebTarget, WebToolSettings


@runtime_checkable
class GuardedPageFetchInterface(Protocol):
    """Fetches one checked target over checked addresses only, bounded in all."""

    @staticmethod
    def system_addresses(host: str, port: int) -> list[str]:
        """Every address the system resolves `host` to; none when the lookup fails."""
        ...

    @staticmethod
    def decoded(raw: bytes, header: str) -> str:
        """`raw` decoded with the page's declared text codec, else UTF-8; never raises."""
        ...

    async def fetch(self, target: WebTarget, settings: WebToolSettings) -> WebPage:
        """The page, or `WebToolRefused` / `WebToolFailed` carrying the hosts reached."""
        ...
