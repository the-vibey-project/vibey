# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seam for the OpenCode runner's pure domain values (ADR-0016)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RunStatusInterface(Protocol):
    """A terminal or in-flight run state, as its string value."""

    @property
    def value(self) -> str: ...


@runtime_checkable
class RunIdInterface(Protocol):
    """A validated run identifier that is safe as a single path segment."""

    @property
    def value(self) -> str: ...


@runtime_checkable
class RunResultInterface(Protocol):
    """The process outcome the application records and the CLI reports."""

    @property
    def status(self) -> RunStatusInterface: ...

    @property
    def returncode(self) -> int: ...

    @property
    def session_id(self) -> str | None: ...

    @property
    def detail(self) -> str: ...

    @property
    def succeeded(self) -> bool: ...
