# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind how `vibey search` and `vibey fetch` may reach the web (SP-LOOPS Phase 6).

Mirrors `vibey/infrastructure/web/session.py::SessionWebAccess` (ADR-0016). Interfaces declare;
they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


@runtime_checkable
class SessionWebAccessInterface(Protocol):
    """A person in-process, a session through the hub, or a session with no web (and why)."""

    @property
    def mode(self) -> Literal["person", "hub", "off"]: ...

    @property
    def hub_url(self) -> str:
        """The hub's address when `mode` is `hub`; empty otherwise."""
        ...

    @property
    def token_file(self) -> Path | None:
        """The session's token file when `mode` is `hub`; None otherwise."""
        ...

    @property
    def reason(self) -> str:
        """Why there is no web when `mode` is `off`; empty otherwise."""
        ...

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> SessionWebAccessInterface:
        """The access the environment declares; never raises."""
        ...
