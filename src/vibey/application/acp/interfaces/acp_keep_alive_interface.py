# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeps the user-level units `vibey acp` loaded running while an editor is connected (ADR-0101).

Implemented by `application/acp/acp_keep_alive.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from vibey.application.acp.dto import AcpSessionContext


@runtime_checkable
class AcpKeepAliveInterface(Protocol):
    def manage(
        self, units: Mapping[str, str], *, hub_label: str | None, deferred: Iterable[str]
    ) -> None:
        """The labels vibey loaded (or found loaded as it renders them) and each one's unit
        file: the only ones it restarts. `hub_label` is the one probed by the hub answering;
        a label in `deferred` is a hub running outside the service manager, taken over (its
        unit loaded) only once that process has gone, never stopped."""
        ...

    def attach(self, session_id: str) -> None:
        """Tell this session what the keep-alive does; the timer runs while any is attached."""
        ...

    def detach(self, session_id: str) -> None:
        """The session closed: nothing more is said to it."""
        ...

    async def probe(self, context: AcpSessionContext | None = None) -> None:
        """Probe the managed units once; when the hub does not answer or a worker is not
        running, take the bootstrap lock, probe again, and only then restart what is still
        down -- at most once per `[acp] probe_seconds` per label. Says one notice per change of
        a label's state, never one per probe. Never raises for a failed probe or restart."""
        ...

    def start(self) -> None:
        """Probe every `[acp] probe_seconds` while units are managed and a session attached."""
        ...

    async def stop(self) -> None:
        """Stop the timer and wait for it; nothing is said afterwards."""
        ...
