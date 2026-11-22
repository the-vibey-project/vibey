# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for asking the user's own service manager from inside `vibey acp` (ADR-0101).

Implemented by `infrastructure/acp/service_manager_runner.py`. Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence


@runtime_checkable
class ServiceManagerRunnerInterface(Protocol):
    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        """Run one of the fixed `launchctl` / `systemctl --user` commands vibey issues, in this
        user's own domain, and return its exit code and standard output, cut to a bound.
        Raises `PermissionError` for any other argv (nothing runs), `TimeoutError` when it gave
        no answer within the bound, and `OSError` when the binary is absent. The binary is
        found on a fixed system PATH, stdin is closed, the environment is minimal."""
        ...
