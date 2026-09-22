# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Secrets implementation of the Secrets port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.secrets import SecretsPort


class InMemorySecrets(SecretsPort):
    """Faked secrets store for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.secrets: dict[str, str] = {}

    async def get_secret(self, key: str) -> str:
        if key not in self.secrets:
            raise KeyError(f"secret {key!r} not found")
        return self.secrets[key]

    async def set_secret(self, key: str, value: str) -> None:
        self.secrets[key] = value
