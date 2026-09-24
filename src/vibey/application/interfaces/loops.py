# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Assembling what `vibey loops` reports: the two loops, their engines by effort, and the
escalation ladder (sub-doctrines 8.b, 8.c)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey.application.dto import EngineContext, LoopsReport


@runtime_checkable
class LoopCatalogInterface(Protocol):
    def report(self, engines: Sequence[EngineContext]) -> LoopsReport:
        """The two loops, the default first, each holding every given engine of its tier in
        the order given, with every effort each can be asked for, and the ladder. Pure data
        assembly: no database, no network, no clock."""
        ...
