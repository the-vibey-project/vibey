# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Secrets manager port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SecretsPort(Protocol):
    """Common protocol for secrets and credential managers."""

    async def get_secret(self, key: str) -> str:
        """Retrieve a stored secret value by its lookup key."""
        ...

    async def set_secret(self, key: str, value: str) -> None:
        """Store a secret value securely under a specified lookup key."""
        ...
