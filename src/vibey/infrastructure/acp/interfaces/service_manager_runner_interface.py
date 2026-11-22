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
        """Run one fixed `launchctl` or `systemctl --user` argv and return its exit code and
        its standard output, cut to a bound. Anything else -- `sudo`, a shell, a `systemctl`
        without `--user`, the `system` launchd domain -- is refused as a result, never run. The
        binary is found on a fixed system PATH, stdin is closed, the environment is minimal
        and the time bounded (an overrun is 124). Raises `OSError` when the binary is absent."""
        ...
