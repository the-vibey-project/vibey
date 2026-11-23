# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey loops marketplace | plugin | mcp | skills | snapshots` (SP-LOOPS
Task 7). Declares only.

Every command reads and writes only the person's own `vibey.toml` (`bootstrap.acp_user_config`)
and the store beside it; none reaches the network except `marketplace update` of a git source.
Each returns its exit code: 0 done, 1 a fetch, lock or run check failed (or nothing to act on),
2 a name, source, ref, URL or command vibey refuses, 78 the person's `vibey.toml` cannot be read
or rewritten.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class LoopsBundleCommandsInterface(Protocol):
    def marketplace_add(self, name: str, source: str, ref: str | None) -> int:
        """Declare a marketplace in `[loops]`; fetch and lock nothing."""
        ...

    def marketplace_update(self, name: str | None) -> int:
        """Fetch, check and lock one declared marketplace (`vibey` re-hashes the shipped one), or
        with no name the shipped one and every declared one."""
        ...

    def marketplace_list(self, *, as_json: bool) -> int:
        """Each marketplace with what the lock says of it; fetches and hashes nothing."""
        ...

    def plugin_add(self, spec: str) -> int:
        """Add `name@marketplace` to `[loops] plugins` (the research default kept)."""
        ...

    def plugin_remove(self, name: str) -> int:
        """Drop every `[loops] plugins` entry named `name`; 1 when there is none."""
        ...

    def mcp_add(
        self,
        name: str,
        *,
        local: bool,
        remote: str | None,
        command: Sequence[str],
        env_allow: Sequence[str],
    ) -> int:
        """Add a local (stdio, `command` stored as given, never through a shell) or remote
        (`https://` only) MCP server to `[loops] mcp_servers`."""
        ...

    def mcp_list(self, *, as_json: bool) -> int:
        """The person's MCP servers."""
        ...

    def skills_list(self, *, as_json: bool) -> int:
        """The skills a run would get, resolved from the lock with no network; the listing's own
        snapshot is removed afterwards."""
        ...

    def snapshots_prune(self, older_than_days: int) -> int:
        """Remove finished runs' snapshots older than `older_than_days` (at least 1)."""
        ...
