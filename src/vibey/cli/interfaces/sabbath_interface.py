# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/sabbath.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from vibey.infrastructure.interfaces.sabbath_interface import HostSabbathGateInterface


class SabbathCommandInterface(Protocol):
    """Sub-doctrine 8.i at the command line (ADR-0070)."""

    def gate(self) -> HostSabbathGateInterface: ...

    def decline_if_resting(self, command: str) -> None:
        """Exit 75 with the reason and the resume time when the Sabbath holds."""
        ...

    def status(self) -> list[str]: ...

    def doctor_lines(self) -> tuple[list[str], bool]: ...
