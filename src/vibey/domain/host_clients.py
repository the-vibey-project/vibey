# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure planner and config merger for `vibey connect` (ADR-0100).

Follows the REA-style host registration workflow (plan -> approval -> backup -> idempotent merge):
- Supports `claude_code`, `claude_desktop`, `codex`, `cursor`, `vscode`, and `gemini_cli`.
- Resolves the absolute `vibey` executable when on `PATH` so GUI hosts (which run with a minimal
  `PATH`) launch `vibey mcp` reliably; falls back to `[sys.executable, "-c", ...]` when `vibey`
  is not on `PATH` (`pyproject.toml` has no `__main__.py`, only `vibey = vibey.cli.main:run`).
- Merges into existing JSON or TOML config files without overwriting sibling MCP servers or keys,
  and reports `unchanged=True` when the file already carries the exact entry.

Pure: no I/O, no `pathlib`, no `os.environ`, no clock. Paths are manipulated as strings.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final, Literal

from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface

ConfigFormat = Literal["json", "toml"]
ConfigScope = Literal["user", "project"]

SERVER_NAME: Final = "vibey"
PYTHON_FALLBACK_CODE: Final = "from vibey.cli.main import run; run(['mcp'])"
TOML_SECTION_RE: Final = re.compile(r"(?ms)^\[mcp_servers\.vibey\]\s*\n.*?(?=^\[|\Z)")


class HostClientError(VibeyError):
    """An unknown client id or an unparseable existing host configuration file."""


@dataclass(frozen=True, slots=True)
class McpLaunchCommand:
    command: str
    args: tuple[str, ...]

    def display(self) -> str:
        return " ".join((self.command, *self.args))


@dataclass(frozen=True, slots=True)
class HostClientSpec:
    client_id: str
    label: str
    scope: ConfigScope
    format: ConfigFormat
    root_key: str
    include_stdio_type: bool
    description: str

    def config_path(self, *, home_dir: str, project_dir: str, platform: str) -> str:
        home = home_dir.rstrip("/")
        proj = project_dir.rstrip("/")
        if self.client_id == "claude_code":
            return f"{proj}/.mcp.json"
        if self.client_id == "claude_desktop":
            if platform == "darwin":
                return f"{home}/Library/Application Support/Claude/claude_desktop_config.json"
            return f"{home}/.config/Claude/claude_desktop_config.json"
        if self.client_id == "codex":
            return f"{home}/.codex/config.toml"
        if self.client_id == "cursor":
            return f"{home}/.cursor/mcp.json"
        if self.client_id == "vscode":
            return f"{proj}/.vscode/mcp.json"
        # gemini_cli
        return f"{home}/.gemini/settings.json"


@dataclass(frozen=True, slots=True)
class ConnectPlanItem:
    client: HostClientSpec
    target_path: str
    backup_path: str | None
    action: Literal["create", "update", "unchanged"]
    new_content: str
    launch: McpLaunchCommand


HOST_CLIENTS: Final[tuple[HostClientSpec, ...]] = (
    HostClientSpec(
        client_id="claude_code",
        label="Claude Code",
        scope="project",
        format="json",
        root_key="mcpServers",
        include_stdio_type=False,
        description="Project-scoped `.mcp.json` read by Claude Code in this repository.",
    ),
    HostClientSpec(
        client_id="claude_desktop",
        label="Claude Desktop",
        scope="user",
        format="json",
        root_key="mcpServers",
        include_stdio_type=False,
        description="User-level `claude_desktop_config.json` for the Claude Desktop app.",
    ),
    HostClientSpec(
        client_id="codex",
        label="OpenAI Codex",
        scope="user",
        format="toml",
        root_key="mcp_servers",
        include_stdio_type=False,
        description="User-level `~/.codex/config.toml` (`[mcp_servers.vibey]`) for Codex CLI and app.",
    ),
    HostClientSpec(
        client_id="cursor",
        label="Cursor",
        scope="user",
        format="json",
        root_key="mcpServers",
        include_stdio_type=False,
        description="User-level `~/.cursor/mcp.json` for Cursor IDE.",
    ),
    HostClientSpec(
        client_id="vscode",
        label="VS Code",
        scope="project",
        format="json",
        root_key="servers",
        include_stdio_type=True,
        description="Workspace `.vscode/mcp.json` (`servers.vibey` with `type: stdio`).",
    ),
    HostClientSpec(
        client_id="gemini_cli",
        label="Gemini CLI",
        scope="user",
        format="json",
        root_key="mcpServers",
        include_stdio_type=False,
        description="User-level `~/.gemini/settings.json` for Gemini CLI and Code Assist.",
    ),
)


class HostClients:
    """Plans and merges MCP server registrations across frontier LLM clients.

    Declared by `interfaces/host_clients_interface.py::HostClientsInterface`.
    """

    def __init__(self, clients: tuple[HostClientSpec, ...] = HOST_CLIENTS) -> None:
        self._clients = clients
        self._by_id = {c.client_id: c for c in clients}

    def all(self) -> tuple[HostClientSpec, ...]:
        return self._clients

    def by_id(self, client_id: str) -> HostClientSpec | None:
        normalized = client_id.strip().lower().replace("-", "_")
        return self._by_id.get(normalized)

    def resolve_clients(self, requested: Sequence[str] | None) -> tuple[HostClientSpec, ...]:
        if not requested:
            return self._clients
        resolved: list[HostClientSpec] = []
        seen: set[str] = set()
        for raw in requested:
            spec = self.by_id(raw)
            if spec is None:
                known = ", ".join(c.client_id for c in self._clients)
                raise HostClientError(f"unknown client {raw!r}; known clients: {known}")
            if spec.client_id not in seen:
                seen.add(spec.client_id)
                resolved.append(spec)
        return tuple(resolved)

    def resolve_launch(
        self,
        *,
        which_vibey: str | None,
        python_executable: str,
    ) -> McpLaunchCommand:
        if which_vibey is not None and which_vibey.strip():
            return McpLaunchCommand(command=which_vibey.strip(), args=("mcp",))
        return McpLaunchCommand(
            command=python_executable,
            args=("-c", PYTHON_FALLBACK_CODE),
        )

    def plan_one(
        self,
        spec: HostClientSpec,
        *,
        home_dir: str,
        project_dir: str,
        platform: str,
        launch: McpLaunchCommand,
        existing_content: str | None,
    ) -> ConnectPlanItem:
        target = spec.config_path(home_dir=home_dir, project_dir=project_dir, platform=platform)
        if spec.format == "json":
            merged = self._merge_json(spec, launch, existing_content, target)
        else:
            merged = self._merge_toml(launch, existing_content, target)

        if existing_content is None:
            return ConnectPlanItem(
                client=spec,
                target_path=target,
                backup_path=None,
                action="create",
                new_content=merged,
                launch=launch,
            )
        if existing_content == merged:
            return ConnectPlanItem(
                client=spec,
                target_path=target,
                backup_path=None,
                action="unchanged",
                new_content=merged,
                launch=launch,
            )
        return ConnectPlanItem(
            client=spec,
            target_path=target,
            backup_path=f"{target}.vibey.bak",
            action="update",
            new_content=merged,
            launch=launch,
        )

    @staticmethod
    def _merge_json(
        spec: HostClientSpec,
        launch: McpLaunchCommand,
        existing_content: str | None,
        target: str,
    ) -> str:
        if existing_content is None or not existing_content.strip():
            doc: dict[str, Any] = {}
        else:
            try:
                parsed = json.loads(existing_content)
            except json.JSONDecodeError as exc:
                raise HostClientError(f"{target}: invalid JSON ({exc.msg})") from exc
            if not isinstance(parsed, dict):
                raise HostClientError(f"{target}: expected a top-level JSON object")
            doc = dict(parsed)

        existing_table = doc.get(spec.root_key)
        if existing_table is None:
            servers: dict[str, Any] = {}
        elif isinstance(existing_table, Mapping):
            servers = dict(existing_table)
        else:
            raise HostClientError(f"{target}: {spec.root_key!r} must be a JSON object")

        entry: dict[str, Any] = {}
        if spec.include_stdio_type:
            entry["type"] = "stdio"
        entry["command"] = launch.command
        entry["args"] = list(launch.args)
        servers[SERVER_NAME] = entry
        doc[spec.root_key] = servers
        return json.dumps(doc, indent=2) + "\n"

    @staticmethod
    def _merge_toml(
        launch: McpLaunchCommand,
        existing_content: str | None,
        target: str,
    ) -> str:
        block = (
            "[mcp_servers.vibey]\n"
            f"command = {json.dumps(launch.command)}\n"
            f"args = [{', '.join(json.dumps(a) for a in launch.args)}]\n"
        )
        if existing_content is None or not existing_content.strip():
            return block

        try:
            parsed = tomllib.loads(existing_content)
        except tomllib.TOMLDecodeError as exc:
            raise HostClientError(f"{target}: invalid TOML ({exc})") from exc

        mcp_servers = parsed.get("mcp_servers")
        if mcp_servers is not None and not isinstance(mcp_servers, Mapping):
            raise HostClientError(f"{target}: 'mcp_servers' must be a TOML table")
        if isinstance(mcp_servers, Mapping):
            existing_vibey = mcp_servers.get(SERVER_NAME)
            if (
                isinstance(existing_vibey, Mapping)
                and existing_vibey.get("command") == launch.command
                and tuple(existing_vibey.get("args", ())) == launch.args
            ):
                return existing_content

        if TOML_SECTION_RE.search(existing_content):
            return TOML_SECTION_RE.sub(block, existing_content, count=1)

        trimmed = existing_content.rstrip()
        return f"{trimmed}\n\n{block}"


HOST_CLIENT_CATALOG: Final[HostClientsInterface] = HostClients()
