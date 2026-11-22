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

    def owns_hub(self) -> bool:
        """Whether the hub is a unit this keep-alive restarts: managed, and not a hub running
        outside the service manager. While it does, nothing else restarts or starts the hub."""
        ...

    def awaiting_handover(self) -> bool:
        """True from the start until step 3 has run (whatever its outcome) when `hub` is among
        `[acp] services`: meanwhile no second hub may be started beside the unit it may load."""
        ...

    def handed_over(self) -> None:
        """Step 3 is over (it ran, failed or was skipped): the hub is this keep-alive's only if
        `manage` said so."""
        ...

    def request_probe(self) -> None:
        """Ask for one probe soon, from any thread (a hub read that found no hub): it joins the
        probe already running, or starts one on the loop. Never restarts anything itself."""
        ...

    def attach(self, session_id: str) -> None:
        """Tell this session what the keep-alive does; the timer runs while any is attached."""
        ...

    def detach(self, session_id: str) -> None:
        """The session closed: nothing more is said to it."""
        ...

    async def probe(self, context: AcpSessionContext | None = None) -> None:
        """Probe the managed units once (one probe at a time, shared); when the hub does not
        answer or a worker is definitely down, take the bootstrap lock, probe again, and only
        then restart what is still down -- at most once per `[acp] probe_seconds` per label --
        holding the lock until a restarted hub answers. With a session's `context`, wait at
        most `[acp] prompt_probe_seconds`; the probe goes on without the wait. Notices are said
        per change of state, damped by `notice_interval_seconds`. Never raises."""
        ...

    def start(self) -> None:
        """Probe every `[acp] probe_seconds` while units are managed and a session attached."""
        ...

    async def stop(self) -> None:
        """Stop the timer and wait for it; nothing is said afterwards."""
        ...
