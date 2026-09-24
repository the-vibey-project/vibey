# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for `vibey-gh slots` (ADR-0016): corpus, calibrate, allowed.

The command line hands this seam its parsed arguments and the loaded configuration; a test
hands it the same and replaces every machine-facing factory, so the composition is tested
exactly while the calibration itself stays evidence. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SlotCommandsInterface(Protocol):
    """The three `vibey-gh slots` actions, each returning a process exit status."""

    def corpus(self, args: Any) -> int:
        """Draw a stratified corpus of turn segments from a turn pool."""
        ...

    def calibrate(self, args: Any) -> int:
        """Sweep N = 1, 2, ... on this device and record the evidence."""
        ...

    def allowed(self, args: Any) -> int:
        """Print how many runs of the model may run at once on this device, and why."""
        ...
