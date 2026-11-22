# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One check `vibey doctor` runs, as data instead of printed lines (SP-ACP).

Implemented by `cli/doctor_probes.py::SectionProbe` over doctor's own sections; `DoctorChecks`
runs them for `vibey doctor` and for `vibey acp`'s bootstrap. Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.dto import DoctorResult


@runtime_checkable
class DoctorProbeInterface(Protocol):
    name: str
    """What the check is called; a check that raises is reported as one `FAIL` of this name."""

    async def run(self) -> tuple[DoctorResult, ...]:
        """Check, and say what was found. Never writes to stdout: under `vibey acp` stdout is
        the protocol stream."""
        ...
