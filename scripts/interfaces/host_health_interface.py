# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/host_health.py` implements. Interfaces declare; they never consume.

A *probe* is `minimum_specs_interface.ProbeInterface`, reused: it measures one part of the
host and returns figures, a skipped one (with the reason) for each it could not measure. A
*ledger* is the append-only weekly record. A *forecaster* turns a host's history into a
replacement forecast. A *renderer* writes the GENERATED blocks. A *condition evaluator*
decides the one tracking issue. A *scheduler renderer* writes the host's weekly unit, and a
*publisher* lands a week's record as a pull request.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class HostIdentityInterface(Protocol):
    """Who the measuring machine is, without anything that identifies its owner."""

    def describe(self) -> dict[str, Any]:
        """Model, chip, memory, cores, OS and a hashed fingerprint; no serial, no host name."""
        ...


class ToolCatalogInterface(Protocol):
    """The tools a platform's probes use, and how its package managers install them."""

    def missing(self) -> list[str]:
        """The declared tools for this platform that are not on PATH."""
        ...

    def command(self, tool: str) -> tuple[str, list[str]] | None:
        """(package manager, argv) that installs `tool` here, or None when none is present."""
        ...

    def hint(self, tool: str) -> str:
        """How to install `tool`, for a skipped figure's reason."""
        ...


class HealthLedgerInterface(Protocol):
    """The JSON-lines record: read whole, appended to, never rewritten."""

    def read(self) -> list[Any]:
        """Every record, in file order; a malformed line is an error naming its number."""
        ...

    def append(self, record: Any) -> bool:
        """Add one record; False (and no write) when its run id is already present."""
        ...


class ForecasterInterface(Protocol):
    """Turns one host's weekly history into the drivers and the machine's replacement date."""

    def forecast(self, history: Sequence[Any]) -> dict[str, Any]:
        """The forecast as of the newest record in `history` (one host, oldest first)."""
        ...


class HealthRendererInterface(Protocol):
    """Writes the record into the page's GENERATED blocks."""

    def blocks(self, records: Sequence[Any]) -> dict[str, str]:
        """Each block's body, keyed by block name."""
        ...

    def apply(self, document: str, records: Sequence[Any]) -> str: ...

    def drift(self, document: str, records: Sequence[Any]) -> list[str]:
        """The names of blocks whose committed body differs from the record's."""
        ...


class ConditionEvaluatorInterface(Protocol):
    """Decides whether the one host-health tracking issue should be open, and what it says."""

    def evaluate(self, records: Sequence[Any], now: str) -> dict[str, Any]:
        """{"raise": bool, "title": str, "body": str, "conditions": [...]}."""
        ...


class SchedulerRendererInterface(Protocol):
    """The weekly unit for the host's own service manager."""

    def launchd(self, argv: Sequence[str], workdir: str, log: str, path_env: str) -> str: ...

    def systemd(
        self, argv: Sequence[str], workdir: str, log: str, path_env: str
    ) -> tuple[str, str]:
        """(the .service, the .timer)."""
        ...


class PublisherInterface(Protocol):
    """Lands the host's records on the integration branch through a pull request."""

    def refresh(self) -> Path:
        """The dedicated clone, fetched and switched to a fresh branch from the base."""
        ...

    def publish(self, records: Sequence[Any], env: Mapping[str, str]) -> str:
        """Merge, render, check, commit, push and open or update the pull request."""
        ...
