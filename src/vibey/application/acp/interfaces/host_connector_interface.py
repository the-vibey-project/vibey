# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey connect` step `vibey acp` runs itself: user-scope clients only (SP-ACP).

Implemented by `infrastructure/acp/host_connector.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import DoctorResult


@runtime_checkable
class HostConnectorInterface(Protocol):
    async def connect_detected(self) -> tuple[DoctorResult, ...]:
        """Register `vibey mcp` with each user-scope client whose config folder already exists
        under the home folder (never a project file in the working directory, never a folder
        it has to create), keeping a `.vibey.bak` of a file it changes. One result per client:
        `PASS` connected (or already), `WARN` its file could not be read or written while the
        others went on, `UNKNOWN` not installed here. Then writes the version's marker."""
        ...

    def already_connected(self) -> bool:
        """True when this vibey version's marker says the clients were connected; a marker
        that is missing, unreadable or malformed is False (connecting again is idempotent)."""
        ...
