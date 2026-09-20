# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application port for best-effort desktop alerts."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DesktopNotifierInterface(Protocol):
    async def notify(self, title: str, message: str) -> bool: ...
