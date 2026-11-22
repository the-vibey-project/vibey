# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The bootstrap's SearXNG step (ADR-0102).

Implemented by `application/acp/acp_searxng_step.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from vibey.application.acp.dto import AcpSessionContext


@runtime_checkable
class AcpSearxngStepInterface(Protocol):
    @property
    def pending(self) -> bool:
        """Whether the step may still ask in this process (allowed, and not settled)."""
        ...

    def wanted(self) -> bool:
        """Whether step 3 keeps vibey's SearXNG unit running: allowed, installed before, and not
        stopped for good. Blocking (it reads the person's record): run it off the loop."""
        ...

    def held_back(self) -> str:
        """What to say when vibey's SearXNG is installed and running from its unit while
        `[acp] searxng = "never"` keeps this session from managing it; "" otherwise. Blocking."""
        ...

    async def offer(
        self,
        context: AcpSessionContext,
        *,
        enter: Callable[[], Awaitable[tuple[bool, str | None]]],
        leave: Callable[[], None],
        notify: Callable[[str, Mapping[str, Any]], Awaitable[None]],
    ) -> None:
        """Offer once per process, inside a prompt turn, to install the local SearXNG; install
        only on the client's explicit "Install SearXNG". `enter` takes the bootstrap's machine
        turn (in-process and cross-process locks) and `leave` gives it back; `notify` sends an
        update unless the session or connection has ended."""
        ...

    async def close(self) -> None:
        """Stop saying anything more (a late notice of an install that outlived its prompt)."""
        ...
