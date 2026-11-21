# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The doctor's checks, run one after another (SP-ACP). Interfaces declare; they never consume."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.acp.interfaces.doctor_probe_interface import DoctorProbeInterface

if TYPE_CHECKING:
    from vibey.application.acp.dto import DoctorResult


@runtime_checkable
class DoctorChecksInterface[P: DoctorProbeInterface](Protocol):
    def each(self) -> AsyncGenerator[tuple[P, tuple[DoctorResult, ...]]]:
        """Run each probe in order and yield it with what it found, as soon as it finishes. A
        probe that raises yields one `FAIL` named after it, and the rest still run; a cancel
        is never turned into a finding."""
        ...

    async def run(self) -> tuple[DoctorResult, ...]:
        """Every probe's results, in order."""
        ...

    @staticmethod
    def passed(results: Sequence[DoctorResult]) -> bool:
        """True when nothing was found `FAIL`."""
        ...
