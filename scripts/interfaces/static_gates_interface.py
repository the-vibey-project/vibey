# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of scripts/static_gates.py: declared here, consumed there (ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class StaticGateEntryInterface(Protocol):
    """One tree checked with `mypy --strict`: its name, its paths, its MYPYPATH (or empty)."""

    @property
    def name(self) -> str: ...

    @property
    def paths(self) -> tuple[str, ...]: ...

    @property
    def mypy_path(self) -> str: ...


class StaticGatesInterface(Protocol):
    """The declared list of trees, the command that checks each, and the run over all of them."""

    def entries(self) -> list[StaticGateEntryInterface]: ...

    def mypy_command(self, entry: StaticGateEntryInterface) -> list[str]: ...

    def env(self, entry: StaticGateEntryInterface, base: Mapping[str, str]) -> dict[str, str]: ...

    def run(self) -> int: ...
