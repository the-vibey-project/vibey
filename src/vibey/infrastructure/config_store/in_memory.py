# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory ConfigStore implementation."""

from __future__ import annotations

from vibey.application.interfaces.config_store import ConfigStorePort


class InMemoryConfigStore(ConfigStorePort):
    def __init__(self) -> None:
        self.configs: dict[str, str] = {}

    async def create_config(self, key: str, value: str) -> None:
        self.configs[key] = value

    async def get_config(self, key: str) -> str:
        if key not in self.configs:
            raise KeyError(f"Config key not found: {key}")
        return self.configs[key]
