# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How the HTTP transport reaches a remote MCP server: one blocking exchange at a time (SP-LOOPS
Phase 5, R13)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey_runners.common.mcp.http_reply import HttpReply


@runtime_checkable
class HttpOpenerInterface(Protocol):
    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> HttpReply:
        """POST `body` to the https `url` with exactly `headers`: no cookie, no credential, no
        proxy from the environment, and no redirect followed (a 3xx is the reply). An error
        status is a reply too, with an empty body. The body holds at most one byte past the
        limit. Raises for a URL that is not https, an exchange that fails, or one that takes
        longer than its deadline."""
        ...

    def delete(self, url: str, headers: Mapping[str, str]) -> int:
        """DELETE the https `url` with exactly `headers` and return the status. Raises as
        `post` does."""
        ...
