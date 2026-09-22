# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Config Store Port Protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfigStorePort(Protocol):
    async def create_config(self, key: str, value: str) -> None: ...

    async def get_config(self, key: str) -> str: ...
