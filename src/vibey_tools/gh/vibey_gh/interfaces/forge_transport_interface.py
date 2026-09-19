# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for talking to a forge's API or CLI (vibey ADR-0016; #138).

Code above this seam asks for data or requests a change; the transport handles
the protocol (HTTP, CLI, etc.) and authentication. A transport returns a a raw
JSON-like result and a problem, so a caller knows if a failure was a protocol
error (e.g., 401 Unauthorized) or a data error (e.g., an empty list).

    All transports are read-only against a specific host. The host is configured
    via `.vibey-gh.toml`.  The shared seam is the decoded `survey` operation;
    command-oriented transports may expose richer operations through their own
    interface (for example, `GhTransportInterface.run`).
"""

from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from typing import Any, Protocol, TypeAlias, runtime_checkable

WorkingDirectory: TypeAlias = str | PathLike[str]


@runtime_checkable
class ForgeTransportInterface(Protocol):
    """Runs a call to a forge and returns the decoded JSON result and a problem."""

    @property
    def executable(self) -> str:
        """The name of the client (e.g., 'gh') or 'http' for direct API calls."""
        ...

    def survey(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[list[Any] | dict[str, Any], str]:
        """The decoded list or object, and a problem that is empty exactly when it answered."""
        ...
