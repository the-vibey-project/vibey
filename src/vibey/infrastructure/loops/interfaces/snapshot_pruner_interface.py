# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over removing runs' snapshots (SP-LOOPS Task 7; Phase 4, Task 8).

Implemented by `snapshot_pruner.py`. Its two methods, `prune` (by age) and `remove` (one run's
folder), are declared once, by the application's `LoopSnapshotRemoverInterface`, which BUILD's
capability service consumes; this is the same seam under the name `vibey loops` already uses.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.loop_capabilities_interface import (
    LoopSnapshotRemoverInterface,
)


@runtime_checkable
class SnapshotPrunerInterface(LoopSnapshotRemoverInterface, Protocol):
    """`prune` and `remove`, as `LoopSnapshotRemoverInterface` declares them."""
