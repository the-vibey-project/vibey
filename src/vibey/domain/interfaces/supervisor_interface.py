# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the declared supervisor (#1189).

Mirrors `vibey/domain/supervisor.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.supervisor import SupervisedService, SupervisorPaths, SupervisorSettings


@runtime_checkable
class SupervisorPlannerInterface(Protocol):
    """Which services the supervisor keeps running, and what each one runs. Pure."""

    def names(self, settings: SupervisorSettings) -> tuple[tuple[str, str], ...]:
        """(name, label) of each supervised service, in `services` order."""
        ...

    def services(
        self, settings: SupervisorSettings, paths: SupervisorPaths
    ) -> tuple[SupervisedService, ...]:
        """The worker, and the delivery bridge unless `[supervisor] delivery` is off.
        Raises ValueError on a setting no service could run with."""
        ...

    def under(self, path: str, roots: tuple[str, ...]) -> str:
        """The first of `roots` that `path` is, or lies under; "" when none."""
        ...


@runtime_checkable
class EnvFileParserInterface(Protocol):
    """Reads a supervisor environment file. Pure."""

    def parse(self, text: str) -> dict[str, str]:
        """Every `KEY=VALUE`, in file order, a later key winning. Raises ValueError
        naming the line number, never its content, on a line that is not one."""
        ...
