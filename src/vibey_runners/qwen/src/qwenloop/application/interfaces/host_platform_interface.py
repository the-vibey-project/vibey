# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application port for the machine a run's shell commands execute on."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class HostPlatformInterface(Protocol):
    def describe(self) -> str:
        """One line naming the host's operating system, release and architecture, and
        what that means for a shell command written for another one."""
        ...
