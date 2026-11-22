# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `tests/system/acp_isolated_agent.py` (ADR-0016). Declares only."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from acp.client.connection import ClientSideConnection


@runtime_checkable
class IsolatedAcpAgentInterface(Protocol):
    """`vibey acp` as a real subprocess an editor would start, sealed off from the machine.

    It runs with a temporary home, XDG folders and an empty `PATH`, and with every `VIBEY_*`
    endpoint pointed at a closed loopback port, so nothing it does can reach the person's own
    configuration, state, units, editors, databases or the network. Its user-level
    `vibey.toml` (the grant, ADR-0101) turns the whole bootstrap off and names the stub hub's
    state folder; the project's `vibey.toml` only narrows, and names a decoy state folder that
    must never be used. Its stdout is read through a tee: every raw line is kept, then handed
    to the official SDK's connection."""

    @property
    def workdir(self) -> Path:
        """The project folder the editor "opened" (the agent's cwd)."""
        ...

    @property
    def state_dir(self) -> Path:
        """The hub state folder the user's `vibey.toml` names (the stub writes into it)."""
        ...

    @property
    def stderr_text(self) -> str:
        """Everything the agent wrote to stderr so far."""
        ...

    @property
    def raw_lines(self) -> tuple[bytes, ...]:
        """Every line the agent wrote to stdout, as read."""
        ...

    def prepare(self, **acp: Any) -> None:
        """Make the folders and write both `vibey.toml` files; `acp` adds keys to the user's
        `[acp]` table."""
        ...

    def environment(self) -> dict[str, str]:
        """The whole environment the agent runs with (nothing is inherited)."""
        ...

    async def start(self, client: Any) -> ClientSideConnection:
        """Start `vibey acp` and connect the SDK's client side to it."""
        ...

    async def stop(self) -> int:
        """Close stdin (EOF), wait a bounded time for the agent to exit, and return its code."""
        ...

    async def kill(self) -> None:
        """Kill the agent's whole process group if it is still running (test cleanup)."""
        ...

    async def wait_stderr(self, text: str, timeout: float, *, count: int = 1) -> bool:
        """Whether `text` appears `count` times on the agent's stderr within `timeout` seconds."""
        ...

    def assert_stdout_was_acp(self) -> None:
        """Every stdout line is one whole JSON-RPC 2.0 message the SDK decoded, and each
        message vibey builds by hand is exactly what the SDK's schema puts on the wire."""
        ...

    def assert_left_no_process(self) -> None:
        """No process is left in the agent's process group."""
        ...

    def assert_machine_untouched(self) -> None:
        """Only the stub's two files are in the state folder, the decoy folder was never made,
        and no unit, client config or editor setting was written under the temporary home."""
        ...

    def run_with_stdin_from_dev_null(self, timeout: float) -> subprocess.CompletedProcess[bytes]:
        """`vibey acp </dev/null`, in the same sealed environment."""
        ...
