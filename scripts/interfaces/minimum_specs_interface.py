# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/minimum_specs.py` implements. Interfaces declare; they never consume.

A *probe* measures one part of the host and returns figures. A *derivation* turns measured
figures into requirements, with the arithmetic recorded. A *staleness policy* merges a
week's figures into the previous record so that a measurement that could not run keeps its
last value, marked stale. A *renderer* writes the record into GENERATED blocks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class CommandRunnerInterface(Protocol):
    """Runs one command and reports what it did; a missing tool is a result, not a crash."""

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> Any:
        """A result carrying `returncode`, `stdout`, `stderr` and `seconds`."""
        ...


class ClockInterface(Protocol):
    """The time, in UTC, for the one place a measurement is stamped."""

    def now(self) -> str:
        """An ISO-8601 UTC timestamp ending in `Z`."""
        ...


class IdleGateInterface(Protocol):
    """Decides whether the host is quiet enough to load and time a model."""

    def wait(self) -> tuple[bool, str, dict[str, Any]]:
        """(idle, the reason when not idle, the conditions observed)."""
        ...

    def foreign_requests_since(self, offset: int) -> int:
        """Inference requests another client made after the log offset `offset`."""
        ...

    def log_offset(self) -> int:
        """The current end of the inference server's log, to measure from."""
        ...


class ProbeInterface(Protocol):
    """Measures one part of the host."""

    name: str

    def run(self) -> list[Any]:
        """Figures: measured or declared ones, and a skipped one for each that could not run."""
        ...


class DerivationsInterface(Protocol):
    """Computes the requirements from the measured figures, recording the arithmetic."""

    def derive(self, figures: Mapping[str, Any]) -> list[Any]:
        """Every derived figure, given the record's figures keyed by id."""
        ...


class DerivationSourceInterface(Protocol):
    """Contributes derived figures: each with its id, formula, inputs and arithmetic."""

    def specs(self) -> list[Any]:
        """The derivations this source declares, in dependency order."""
        ...


class PackageManagerInterface(Protocol):
    """A Linux distribution's package manager, driven from the declared configuration."""

    def installed(self) -> set[str]:
        """The names of every installed package."""
        ...

    def sizes(self) -> dict[str, int]:
        """Installed size in bytes, by package name."""
        ...

    def install(self, packages: Sequence[str]) -> Any:
        """Installs `packages`; the command's result."""
        ...

    def version(self, package: str) -> str | None:
        """The highest version the repositories offer for `package`, or None."""
        ...


class CellRunnerInterface(Protocol):
    """Runs one (distribution x architecture) cell of the Linux matrix and hands back a
    partial record: measured in the distribution's container, or skipped with the reason."""

    def run(self, distro: str, arch: str) -> Any:
        """The partial record for the cell."""
        ...


class StalenessPolicyInterface(Protocol):
    """Merges a run's figures into the previous record."""

    def merge(self, previous: Sequence[Any], fresh: Sequence[Any]) -> list[Any]:
        """The figures to record: fresh ones, and previous values marked stale where needed."""
        ...


class RequirementsRendererInterface(Protocol):
    """Writes the record into a document's GENERATED blocks."""

    def blocks(self, record: Any) -> dict[str, str]:
        """Every block this renderer owns, keyed by name, as the text between its markers."""
        ...

    def apply(self, document: str, record: Any) -> str:
        """`document` with every owned block replaced by its regenerated text."""
        ...

    def drift(self, document: str, record: Any) -> list[str]:
        """The names of the owned blocks that regeneration would change (or that are missing)."""
        ...
