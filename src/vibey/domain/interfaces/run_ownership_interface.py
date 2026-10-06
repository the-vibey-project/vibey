# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind binding a workflows run to the principal that started it.

Mirrors `vibey/domain/run_ownership.py` (ADR-0016, ADR-0085). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RunOwnershipInterface(Protocol):
    """Mints request ids bound to an owner, and verifies them."""

    def mint(self, owner: str, nonce: str) -> str:
        """The request id for a run `owner` starts, from a fresh hex `nonce`."""
        ...

    def owns(self, owner: str, request_id: str) -> bool:
        """True only when `request_id` was minted for `owner`; constant-time on the tag."""
        ...
