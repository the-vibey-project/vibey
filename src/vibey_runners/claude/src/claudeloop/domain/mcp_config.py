# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An MCP server from a run's capability snapshot, as the SDK config one session is given
(SP-LOOPS Phase 4, Task 5; R7).

Every config names its transport, so nothing is left to the SDK's or Claude Code's default:

- `local` is `{"type": "stdio"}`, and its command is the scrubbed launcher
  (`vibey_runners.common.capabilities.scrubbed_exec`, run as `python -I -m`), given one
  `--allow NAME` for each name in `env_allow`, then `--`, then the server's own argv. The
  launcher keeps only those names, reads
  their values from the environment it inherits, and execs the server. The config has no `env`
  key, ever: an environment value never reaches an argv, a file or a log through it.
- `remote` is `{"type": "http"}` (streamable HTTP), never `sse`.

Pure: no environment, no clock. The launcher prefix is given by the composition root. Declared
by `interfaces/mcp_config_translator_interface.py::McpConfigTranslatorInterface`.
"""

from __future__ import annotations

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.scrubbed_launch import ScrubbedLaunch


class McpConfigTranslator:
    """Declared by `interfaces/mcp_config_translator_interface.py`. A local server's argv is
    `ScrubbedLaunch`'s, the family's one builder of it (SP-LOOPS Phase 5, R14); it refuses an
    empty launcher."""

    def __init__(self, launcher: tuple[str, ...]) -> None:
        self._launch = ScrubbedLaunch(launcher)

    def translate(self, server: McpServerSpec) -> dict[str, object]:
        if server.trust == "local" and server.command:
            command, *args = self._launch.argv(server)
            return {"type": "stdio", "command": command, "args": args}
        if server.trust == "remote" and server.url is not None:
            return {"type": "http", "url": server.url}
        raise ValueError(
            f"MCP server {server.name!r} is neither a local server with a command nor a "
            "remote server with a URL"
        )
