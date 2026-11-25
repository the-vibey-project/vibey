# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for finding the `vibey` a session runs (SP-LOOPS Phase 6). Interfaces declare;
they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VibeyCommandInterface(Protocol):
    """Which `vibey` a session's web tools, or its `vibey-web` connector, run."""

    def resolve(self) -> str:
        """The `vibey` console script installed beside this process's own Python, when there is
        an executable one; else the one on PATH; else the bare name."""
        ...
