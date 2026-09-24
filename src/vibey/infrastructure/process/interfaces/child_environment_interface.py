# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for building a model-driven child process's environment.

Mirrors `vibey/infrastructure/process/child_environment.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


@runtime_checkable
class ForbiddenEnvironmentInterface(Protocol):
    """Names no allow-list may admit, whatever it declares."""

    @property
    def prefixes(self) -> tuple[str, ...]:
        """Every name starting with one of these is forbidden."""
        ...

    @property
    def markers(self) -> tuple[str, ...]:
        """Every name containing one of these is forbidden."""
        ...

    def forbids(self, name: str) -> bool:
        """Whether `name` may never reach a child."""
        ...

    def forbids_prefix(self, prefix: str) -> bool:
        """Whether a declared prefix could admit a forbidden name."""
        ...


@runtime_checkable
class EnvironmentAllowListInterface(Protocol):
    """The names and prefixes a child may receive, under a rule nothing can widen."""

    @property
    def names(self) -> frozenset[str]:
        """Exact names admitted."""
        ...

    @property
    def prefixes(self) -> tuple[str, ...]:
        """Prefixes admitted (declared with a trailing `*`)."""
        ...

    @property
    def forbidden(self) -> ForbiddenEnvironmentInterface:
        """The rule every entry, and every admitted name, is checked against."""
        ...

    def entries(self) -> tuple[str, ...]:
        """Every entry as it would be declared: names, then prefixes with their `*`."""
        ...

    def admits(self, name: str) -> bool:
        """Whether `name` may reach the child: declared, and not forbidden."""
        ...

    def extended(
        self,
        entries: Iterable[str],
        *,
        forbidden: ForbiddenEnvironmentInterface | None = None,
        where: str = ...,
    ) -> "EnvironmentAllowListInterface":
        """This list plus `entries`, all re-checked under `forbidden`; raises
        ValueError on an entry the rule refuses."""
        ...


@runtime_checkable
class ChildEnvironmentInterface(Protocol):
    """Builds the environment one kind of child process starts with."""

    def build(self) -> dict[str, str]:
        """The environment, read from the source at call time: allow-listed names only,
        vibey's Python environment stripped, the caller's overlay laid over it last."""
        ...
