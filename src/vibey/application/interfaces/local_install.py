# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Protocols for local dependency installation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.domain.local_stack import (
    DependencyReport,
    DependencySpec,
    HostOs,
    LocalStackReport,
)


@runtime_checkable
class DependencyInstaller(Protocol):
    key: str

    def check(self) -> DependencyReport: ...
    def install(self) -> DependencyReport: ...


@runtime_checkable
class LocalStackInstallerInterface(Protocol):
    def check(self) -> LocalStackReport: ...
    def install(self) -> LocalStackReport: ...


@runtime_checkable
class LocalStackFactory(Protocol):
    def host(self) -> HostOs | None: ...
    def host_label(self) -> str: ...
    def precondition(self) -> str | None: ...
    def build(
        self, specs: tuple[DependencySpec, ...], *, model: str
    ) -> LocalStackInstallerInterface: ...


__all__ = [
    "DependencyInstaller",
    "LocalStackInstallerInterface",
    "LocalStackFactory",
]
