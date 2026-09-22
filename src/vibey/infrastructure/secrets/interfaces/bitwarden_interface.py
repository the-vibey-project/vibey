# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Bitwarden secrets seam.

Mirrors `vibey/infrastructure/secrets/bitwarden.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.secrets import SecretsPort


@runtime_checkable
class BitwardenSecretsAdapterInterface(SecretsPort, Protocol):
    """The self-hosted Bitwarden implementation of the Secrets port."""
