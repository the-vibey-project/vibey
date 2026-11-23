# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP server the person configured (design Decision 9).

`local` is a stdio server: `command` is its argv and `url` is None. `remote` is an HTTPS server:
`url` is set and `command` is None. `env_allow` names the only environment variables a local
server's scrubbed environment may keep. The trust level decides egress, budget and which
sessions mount the server; it never makes the server's output instruction. A record with no
behaviour, so no seam of its own.
"""

from dataclasses import dataclass
from typing import Literal

McpTrust = Literal["local", "remote"]


@dataclass(frozen=True, slots=True)
class McpServerSpec:
    name: str
    trust: McpTrust
    command: tuple[str, ...] | None
    url: str | None
    env_allow: tuple[str, ...]
