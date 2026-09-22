# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The OpenBao secrets seam.

Mirrors `vibey/infrastructure/secrets/openbao.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.secrets import SecretsPort


@runtime_checkable
class OpenBaoSecretsAdapterInterface(SecretsPort, Protocol):
    """The self-hosted OpenBao implementation of the Secrets port."""
