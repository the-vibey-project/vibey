# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One engine run's web access, opened as it starts and closed when it ends (SP-LOOPS Phase 6,
Task 5; R1, R4).

**Open.** A run with no owner-only folder of its own (an engine that takes no capability
snapshot) has nowhere a token may live (R1), so it has no web (`NO_RUN_FOLDER`) and the hub is not
even asked. Otherwise the running hub is looked for the way every client finds it
(`HubLocatorInterface`); with none, nothing is minted and nothing written (`NO_HUB`). With one,
the run's own web-only principal is minted into its folder with the wall clock's now -- the hub
reads expiry against its own wall clock (`vibey serve`'s `time.time`) -- and the run holds it.
A mint that is refused (`SessionGrantRefused`) or cannot be written (`OSError`) is logged by
principal and error class and the run has no web (`NO_TOKEN`): a run is never stopped for want
of search, and the plan says why it has none.

**Close** revokes the grant. It runs on every exit -- normal, failure, cancellation -- and
before the run's folder is released (the folder going takes the token file, but not the hub's
registry entry). A revocation that fails is logged and swallowed, so the run's own outcome is
never replaced by it; the grant still expires at the run deadline plus the margin (R4), and the
start-up sweep removes what is left (Task 7).

Never logs, raises or returns a token. Declared by
`interfaces/run_web_grants_interface.py::RunWebGrantsInterface`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from vibey.application.dto import RunWebAccess
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.run_web_grants_interface import HubLocatorInterface
from vibey.application.interfaces.session_web_principals_interface import (
    SessionWebPrincipalsInterface,
)
from vibey.domain.errors import SessionGrantRefused
from vibey.domain.session_principal import SESSION_PRINCIPAL_PREFIX
from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER, NO_TOKEN


class RunWebGrants:
    """Declared by `interfaces/run_web_grants_interface.py::RunWebGrantsInterface`."""

    def __init__(
        self,
        *,
        hub: HubLocatorInterface,
        principals: SessionWebPrincipalsInterface,
        clock: Callable[[], float] = time.time,
        logger: Logger | None = None,
    ) -> None:
        self._hub = hub
        self._principals = principals
        self._clock = clock
        self._logger = logger

    def open(self, run_id: UUID, folder: Path | None) -> RunWebAccess:
        if folder is None:
            return RunWebAccess("none", reason=NO_RUN_FOLDER)
        url = self._hub.url()
        if url is None:
            return RunWebAccess("none", reason=NO_HUB)
        try:
            grant = self._principals.mint(run_id, folder, self._clock())
        except (SessionGrantRefused, OSError) as refused:
            self._warn(
                "session_web_grant_refused",
                principal=f"{SESSION_PRINCIPAL_PREFIX}{run_id}",
                error=type(refused).__name__,
            )
            return RunWebAccess("none", reason=NO_TOKEN)
        return RunWebAccess("hub", hub_url=url, grant=grant)

    def close(self, access: RunWebAccess) -> None:
        if access.grant is None:
            return
        try:
            self._principals.revoke(access.grant)
        except Exception as failed:  # noqa: BLE001 - logged; never replaces the run's outcome
            self._warn(
                "session_web_revoke_failed",
                principal=access.grant.name,
                error=type(failed).__name__,
            )

    def _warn(self, event: str, **fields: str) -> None:
        if self._logger is not None:
            self._logger.warning(event, **fields)
