# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Removes the session registry's expired entries, once, as a worker starts (SP-LOOPS Phase 6,
Task 7; R4).

A session's grant is revoked when its run ends. A worker that crashed or was killed never got
there: the run's token file went, or goes, with its run folder under the snapshot sweep
(`LoopCapabilitiesService.sweep`), but its entry stays in the hub's registry until its expiry --
refused by the hub from then on (`SessionPrincipalPolicy.expired`), so this is disk hygiene, not
security. The sweep removes exactly the entries whose principal has expired by the wall clock (the
clock the worker mints with and the hub reads expiry by), so no live session is ever cut short,
and never one it could not read: an unreadable entry is named and kept. Two workers sweeping at
once each remove what they find; an entry the other removed first is counted by neither twice.

Declared by `interfaces/session_registry_sweep_interface.py::SessionRegistrySweepInterface`.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable

from vibey.application.dto import SessionSweepReport
from vibey.application.interfaces.session_registry_sweep_interface import (
    SessionPrincipalListingInterface,
)
from vibey.domain.interfaces.session_principal_interface import SessionPrincipalPolicyInterface
from vibey.domain.session_principal import SESSION_PRINCIPALS


class SessionRegistrySweep:
    """Declared by
    `interfaces/session_registry_sweep_interface.py::SessionRegistrySweepInterface`."""

    def __init__(
        self,
        registry: SessionPrincipalListingInterface,
        *,
        clock: Callable[[], float] = time.time,
        policy: SessionPrincipalPolicyInterface = SESSION_PRINCIPALS,
    ) -> None:
        self._registry = registry
        self._clock = clock
        self._policy = policy

    def sweep(self) -> SessionSweepReport:
        now = self._clock()
        if not math.isfinite(now):
            raise ValueError(f"the sweep needs a finite now to judge expiry by, not {now}")
        listing = self._registry.entries()
        removed: list[str] = []
        kept = 0
        for entry in listing.entries:
            if not self._policy.expired(entry.principal, now):
                kept += 1
            elif self._registry.forget(entry.digest):
                removed.append(entry.principal.name)
        return SessionSweepReport(removed=tuple(removed), kept=kept, refused=listing.unreadable)
