# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the driver's handoff brief (ADR-0070).

Mirrors `vibey/domain/driver_brief.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.driver_brief import DriverBrief
    from vibey.domain.handoff import GateMode, GateResult


@runtime_checkable
class DriverGateInterface(Protocol):
    """Verifies a driver brief against the transcript digest read now. Pure."""

    def verify(
        self, brief: DriverBrief, *, digest_now: str | None, mode: GateMode, attempts: int
    ) -> GateResult: ...


@runtime_checkable
class DriverBriefRendererInterface(Protocol):
    """The brief as the text the receiving engine reads first."""

    def render(self, brief: DriverBrief) -> str: ...
