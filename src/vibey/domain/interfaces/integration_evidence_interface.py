# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind REVIEW's integration gate evidence.

Mirrors `vibey/domain/integration_evidence.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GateRunInterface(Protocol):
    """One verification command run against the integration branch."""

    @property
    def command(self) -> str: ...

    @property
    def returncode(self) -> int: ...

    @property
    def output_tail(self) -> str: ...

    @property
    def passed(self) -> bool: ...

    def to_payload(self) -> dict[str, object]: ...


@runtime_checkable
class ItemEvidenceInterface(Protocol):
    """Every gate run for one work item's integration. No runs means unmeasured."""

    @property
    def work_item_id(self) -> str: ...

    @property
    def measured(self) -> bool: ...

    def to_payload(self, *, cycle: int) -> dict[str, object]:
        """The `ArtifactProduced` payload a successful integrate records."""
        ...


@runtime_checkable
class IntegrationEvidenceInterface(Protocol):
    """A cycle's integration gate evidence: the latest record per work item."""

    @property
    def unmeasured(self) -> tuple[str, ...]:
        """The work items whose integration ran no verification command."""
        ...

    @property
    def measured(self) -> bool:
        """True only when there is a record and every item ran at least one gate."""
        ...

    def statement(self) -> str:
        """One plain sentence for the reviewer and for a gate prompt."""
        ...

    def junit_xml(self) -> str:
        """A JUnit report of exactly what ran."""
        ...

    def coverage_json(self) -> str:
        """Coverage is not measured by vibey, so it is never claimed."""
        ...
