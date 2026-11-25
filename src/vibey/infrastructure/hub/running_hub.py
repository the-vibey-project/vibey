# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub running on this computer, as a worker finds it to give a session its address
(SP-LOOPS Phase 6, Task 5).

The one way every client already finds the hub, not a second one: the runtime record
(`serving.json`, `LocalTokenStore.serving`) in the hub's state folder, believed only while the
process it names holds the hub's lock (`ServeLock.held_by`, as `HubGateway._live` and
`vibey hub status` check it), and only at the fixed loopback literal its host maps to
(`HUB_TARGETS.loopback_address`, never the name resolved again). A record that is missing,
malformed, stale or names another computer is no hub. Nothing is connected to: whether the hub
answers is the session's own call to find out, and a hub that stops after the session starts
refuses it the same way.

Declared by `interfaces/running_hub_interface.py::RunningHubInterface`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from vibey.application.interfaces.observability import Logger
from vibey.domain.hub_target import HUB_TARGETS
from vibey.infrastructure.hub.local_token import LocalTokenStore
from vibey.infrastructure.hub.serve_lock import ServeLock


class RunningHub:
    """Declared by `interfaces/running_hub_interface.py::RunningHubInterface`."""

    def __init__(
        self,
        state_dir: Path,
        *,
        holder: Callable[[Path], int | None] = lambda state: ServeLock(state).held_by(),
        logger: Logger | None = None,
    ) -> None:
        self._state_dir = state_dir
        self._holder = holder
        self._logger = logger

    def url(self) -> str | None:
        try:
            record = LocalTokenStore(self._state_dir).serving()
        except ValueError as unreadable:
            # The message names the record's path and what is wrong with it; it holds no secret.
            self._warn("hub_record_unreadable", error=str(unreadable))
            return None
        if record is None or self._holder(self._state_dir) != record.pid:
            return None
        host = HUB_TARGETS.loopback_address(record.host)
        if host is None:
            self._warn("hub_record_not_loopback", state_dir=str(self._state_dir))
            return None
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        return f"{scheme}://{shown}:{record.port}"

    def _warn(self, event: str, **fields: str) -> None:
        if self._logger is not None:
            self._logger.warning(event, **fields)
