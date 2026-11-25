# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams over an engine run's web access (SP-LOOPS Phase 6, Task 5).

`RunWebGrantsInterface` is what a BUILD run consumes: it opens the run's web access as the run
starts (its own grant from the running hub, or none and why) and closes it when the run ends,
however it ends. `HubLocatorInterface` is what that service consumes to learn whether a hub is
running, and infrastructure implements (`infrastructure/hub/running_hub.py`). Interfaces
declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import RunWebAccess


@runtime_checkable
class HubLocatorInterface(Protocol):
    """Where the hub running on this computer answers, if one is."""

    def url(self) -> str | None:
        """The running hub's loopback URL (`http://127.0.0.1:<port>`, no path; `https` when the
        hub serves TLS), or None when no hub is running: no runtime record, one that cannot be
        read, one whose process does not hold the hub's lock, or one naming an address that is
        not loopback. Found the way every other client finds it (`serving.json` in the hub's
        state folder, checked against the lock), never by asking the network."""
        ...


@runtime_checkable
class RunWebGrantsInterface(Protocol):
    """Opens and closes one engine run's web access."""

    def open(self, run_id: UUID, folder: Path | None) -> RunWebAccess:
        """The run's web access. With no `folder` (the run has no owner-only folder of its own)
        it is none, `NO_RUN_FOLDER`, and the hub is not asked; with no running hub it is none,
        `NO_HUB`, and nothing is written; otherwise a grant is minted into `folder` with the
        wall clock's now and the access is `hub`. A grant that cannot be minted is logged by
        principal and error class, never by token, and the access is none, `NO_TOKEN`. Never
        raises for any of these."""
        ...

    def close(self, access: RunWebAccess) -> None:
        """Revokes the access's grant, if it has one; idempotent. A revocation that fails is
        logged (never with a token) and swallowed, so it never takes the place of the run's own
        outcome."""
        ...
