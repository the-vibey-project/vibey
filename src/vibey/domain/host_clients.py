# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure planner and config merger for `vibey connect` (ADR-0100, SP-ACP).

Follows the REA-style host registration workflow (plan -> approval -> backup -> idempotent merge):
- Supports `claude_code`, `claude_desktop`, `codex`, `cursor`, `vscode` and `gemini_cli` over
  MCP (`vibey mcp`), and `zed` over ACP (`vibey acp`, as a custom agent server).
- Each entry runs the absolute `vibey` the caller resolved (the running install's own launcher)
  so GUI hosts (which run with a minimal `PATH`) launch it reliably; falls back to
  `[sys.executable, "-c", ...]` when there is none (`pyproject.toml` has no `__main__.py`, only
  `vibey = vibey.cli.main:run`).
- Merges into existing JSON or TOML config files without overwriting sibling servers or keys,
  and reports `unchanged` -- never rewriting or reformatting the file -- when it already carries
  a `vibey` entry running the same command with the same leading arguments. An entry the person
  customised keeps everything vibey does not need to change: its `env`, other keys, and flags
  after vibey's own arguments (`["acp", "--no-bootstrap"]`). A rewrite keeps the file's
  indentation and its non-ASCII text.
- Never rewrites a JSON file it cannot read as strict JSON. Editors such as Zed keep comments
  and trailing commas in their settings; such a file is read leniently only to see whether it
  already carries the entry (then it is `unchanged`), and is otherwise refused with the exact
  snippet to paste by hand. A file nested too deeply to parse is refused the same way, never
  with a traceback.

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
ClientProtocol = Literal["mcp", "acp"]

SERVER_NAME: Final = "vibey"
PYTHON_FALLBACK_CODE: Final = (
    "import sys; from vibey.cli.main import run; run(['mcp', *sys.argv[1:]])"
)
PYTHON_FALLBACK_CODES: Final[Mapping[ClientProtocol, str]] = {
    "mcp": PYTHON_FALLBACK_CODE,
    "acp": "import sys; from vibey.cli.main import run; run(['acp', *sys.argv[1:]])",
}
"""`python -c CODE [flags...]`: the flags after the code reach `vibey mcp` / `vibey acp`, as they
do after the console script's own `mcp` / `acp`."""
EARLIER_FALLBACK_CODES: Final[Mapping[ClientProtocol, str]] = {
    "mcp": "from vibey.cli.main import run; run(['mcp'])",
    "acp": "from vibey.cli.main import run; run(['acp'])",
}
"""The fallback vibey wrote before it passed flags through; an entry carrying it is rewritten,
keeping the flags after it."""
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
    protocol: ClientProtocol = "mcp"
    """What the entry launches: `vibey mcp` (an MCP server) or `vibey acp` (an ACP agent)."""
    entry_type: str | None = None
    """When set, the entry's `type` and an empty `env` (Zed's custom agent servers)."""

    def config_path(
        self,
        *,
        home_dir: str,
        project_dir: str,
        platform: str,
        xdg_config_home: str | None = None,
    ) -> str:
        """Where the client's config lives. `xdg_config_home` is the environment's
        `XDG_CONFIG_HOME`, used only where the client honours it (Zed on Linux) and only when
        absolute; Zed on macOS always reads `~/.config/zed`."""
        home = home_dir.rstrip("/")
        proj = project_dir.rstrip("/")
        if self.client_id == "zed":
            xdg = (xdg_config_home or "").rstrip("/")
            if platform != "darwin" and xdg.startswith("/"):
                return f"{xdg}/zed/settings.json"
            return f"{home}/.config/zed/settings.json"
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

    def presence_path(
        self, *, home_dir: str, platform: str, xdg_config_home: str | None = None
    ) -> str:
        """The folder whose existence says this client is installed for this user: its
        config folder for a user-scope client, its own user folder for a project-scope one."""
        home = home_dir.rstrip("/")
        if self.client_id == "claude_code":
            return f"{home}/.claude"
        if self.client_id == "vscode":
            if platform == "darwin":
                return f"{home}/Library/Application Support/Code"
            return f"{home}/.config/Code"
        config = self.config_path(
            home_dir=home, project_dir="", platform=platform, xdg_config_home=xdg_config_home
        )
        return config.rsplit("/", 1)[0]


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
    HostClientSpec(
        client_id="zed",
        label="Zed",
        scope="user",
        format="json",
        root_key="agent_servers",
        include_stdio_type=False,
        description="User-level `~/.config/zed/settings.json` (`agent_servers.vibey`) registers "
        "`vibey acp` as an external agent.",
        protocol="acp",
        entry_type="custom",
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
        protocol: ClientProtocol = "mcp",
    ) -> McpLaunchCommand:
        if which_vibey is not None and which_vibey.strip():
            return McpLaunchCommand(command=which_vibey.strip(), args=(protocol,))
        return McpLaunchCommand(
            command=python_executable,
            args=("-c", PYTHON_FALLBACK_CODES[protocol]),
        )

    @staticmethod
    def entry(spec: HostClientSpec, launch: McpLaunchCommand) -> dict[str, Any]:
        """The `vibey` entry a JSON client's table carries."""
        entry: dict[str, Any] = {}
        if spec.entry_type is not None:
            entry["type"] = spec.entry_type
        elif spec.include_stdio_type:
            entry["type"] = "stdio"
        entry["command"] = launch.command
        entry["args"] = list(launch.args)
        if spec.entry_type is not None:
            entry["env"] = {}
        return entry

    def snippet(self, spec: HostClientSpec, launch: McpLaunchCommand) -> str:
        """What to paste into a JSON client's top-level object by hand."""
        table = json.dumps({SERVER_NAME: self.entry(spec, launch)})
        return f"{json.dumps(spec.root_key)}: {table}"

    def plan_one(
        self,
        spec: HostClientSpec,
        *,
        home_dir: str,
        project_dir: str,
        platform: str,
        launch: McpLaunchCommand,
        existing_content: str | None,
        xdg_config_home: str | None = None,
    ) -> ConnectPlanItem:
        target = spec.config_path(
            home_dir=home_dir,
            project_dir=project_dir,
            platform=platform,
            xdg_config_home=xdg_config_home,
        )
        if spec.format == "json":
            merged = self._merge_json(spec, launch, existing_content, target)
        else:
            merged = self._merge_toml(spec, launch, existing_content, target)

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

    def _merge_json(
        self,
        spec: HostClientSpec,
        launch: McpLaunchCommand,
        existing_content: str | None,
        target: str,
    ) -> str:
        bom, text = self._without_bom(existing_content)
        if text is None or not text.strip():
            doc: dict[str, Any] = {}
        else:
            try:
                parsed = json.loads(text)
            except (ValueError, RecursionError) as exc:
                # RecursionError: deep nesting (a hostile `[[[[...`), which the decoder does not
                # report as a JSONDecodeError. Either way the file is not rewritten.
                if self._carries(spec, launch, self._lenient(text)):
                    return existing_content or ""  # pasted by hand: already right, kept as is
                why = exc.msg if isinstance(exc, json.JSONDecodeError) else "nested too deeply"
                raise HostClientError(
                    f"{target}: invalid JSON ({why}): not strict JSON (comments or trailing "
                    "commas), so vibey does not rewrite it. Add this to its top-level object by "
                    f"hand: {self.snippet(spec, launch)}"
                ) from exc
            if not isinstance(parsed, dict):
                raise HostClientError(f"{target}: expected a top-level JSON object")
            if self._carries(spec, launch, parsed):
                return existing_content or ""  # already connected: not reformatted
            doc = dict(parsed)

        existing_table = doc.get(spec.root_key)
        if existing_table is None:
            servers: dict[str, Any] = {}
        elif isinstance(existing_table, Mapping):
            servers = dict(existing_table)
        else:
            raise HostClientError(f"{target}: {spec.root_key!r} must be a JSON object")

        servers[SERVER_NAME] = self._updated(spec, launch, servers.get(SERVER_NAME))
        doc[spec.root_key] = servers
        return bom + json.dumps(doc, indent=self._indent(text), ensure_ascii=False) + "\n"

    def carries(
        self, spec: HostClientSpec, launch: McpLaunchCommand, existing_content: str | None
    ) -> bool:
        """Whether `existing_content` already holds a `vibey` entry that runs this launch,
        however it is laid out (a JSON file with comments is read leniently) and whatever else
        the person added to it (`_connected`). A file that cannot be parsed at all -- nested too
        deeply included -- does not. Only reads."""
        _, text = self._without_bom(existing_content)
        if text is None or not text.strip():
            return False
        if spec.format == "toml":
            try:
                return self._toml_carries(spec, tomllib.loads(text), launch)
            except (ValueError, RecursionError):
                return False
        try:
            doc = json.loads(text)
        except (ValueError, RecursionError):
            doc = self._lenient(text)
        return self._carries(spec, launch, doc)

    def names_vibey(self, spec: HostClientSpec, existing_content: str | None) -> bool:
        """Whether the file holds any `vibey` entry at all, whatever it runs. Only reads; a
        file that cannot be parsed holds none."""
        _, text = self._without_bom(existing_content)
        if text is None or not text.strip():
            return False
        doc: object
        if spec.format == "toml":
            try:
                doc = tomllib.loads(text)
            except (ValueError, RecursionError):
                return False
        else:
            try:
                doc = json.loads(text)
            except (ValueError, RecursionError):
                doc = self._lenient(text)
        table = doc.get(spec.root_key) if isinstance(doc, Mapping) else None
        return isinstance(table, Mapping) and SERVER_NAME in table

    def _carries(self, spec: HostClientSpec, launch: McpLaunchCommand, doc: object) -> bool:
        """Whether a parsed document's table holds a `vibey` entry that runs this launch."""
        if not isinstance(doc, Mapping):
            return False
        table = doc.get(spec.root_key)
        return isinstance(table, Mapping) and self._connected(spec, launch, table.get(SERVER_NAME))

    def _connected(self, spec: HostClientSpec, launch: McpLaunchCommand, existing: object) -> bool:
        """Whether an existing entry already runs this launch.

        In a user-scope file (the person's own config): the same command, `args` that start
        with the launch's own (any flag after them, such as `--no-bootstrap`, is the person's),
        and the `type` the client needs; every other key (`env`, ...) is the person's and never
        decides it. In a project-scope file (`.mcp.json`, `.vscode/mcp.json`: whatever the
        repository holds) only the exact canonical entry counts: a planted `env`, `envFile`,
        other key or extra argument would run inside vibey's trusted server."""
        if spec.scope != "user":
            return isinstance(existing, Mapping) and dict(existing) == self.entry(spec, launch)
        if not isinstance(existing, Mapping):
            return False
        args = existing.get("args")
        wanted = spec.entry_type or ("stdio" if spec.include_stdio_type else None)
        return (
            existing.get("command") == launch.command
            and isinstance(args, list)
            and tuple(args[: len(launch.args)]) == launch.args
            and (wanted is None or existing.get("type") == wanted)
            and (spec.entry_type is None or isinstance(existing.get("env", {}), Mapping))
        )

    def _updated(
        self, spec: HostClientSpec, launch: McpLaunchCommand, existing: object
    ) -> dict[str, Any]:
        """The entry to write over an existing one: only what must change changes -- `type`,
        `command`, and the launch's own `args` (the person's flags after them are kept) --
        and every other key, `env` included, is kept as the person wrote it. Only in a user-scope
        file: a project-scope entry is always written canonical, whole (see `_connected`)."""
        entry = self.entry(spec, launch)
        if spec.scope != "user" or not isinstance(existing, Mapping):
            return entry
        kept: dict[str, Any] = dict(existing)
        for key in ("type", "command"):
            if key in entry:
                kept[key] = entry[key]
        kept["args"] = [*launch.args, *self._extra_args(existing.get("args"), spec.protocol)]
        if spec.entry_type is not None and not isinstance(kept.get("env"), Mapping):
            kept["env"] = {}
        return kept

    @staticmethod
    def _extra_args(args: object, protocol: ClientProtocol) -> list[str]:
        """The person's own flags after vibey's launch arguments (`["acp", "--no-bootstrap"]`
        keeps `--no-bootstrap`), whichever launcher wrote them; none for any other shape."""
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            return []
        if args[:1] == [protocol]:
            return list(args[1:])
        if args[:1] == ["-c"] and args[1:2] in (
            [PYTHON_FALLBACK_CODES[protocol]],
            [EARLIER_FALLBACK_CODES[protocol]],
        ):
            return list(args[2:])
        return []

    @staticmethod
    def _without_bom(text: str | None) -> tuple[str, str | None]:
        """A UTF-8 byte-order mark, kept apart so the rest is read as JSON or TOML and a
        rewrite puts it back."""
        if text is not None and text.startswith("\ufeff"):
            return "\ufeff", text[1:]
        return "", text

    @staticmethod
    def _indent(text: str | None) -> int | str:
        """The file's own indentation unit (its first indented line's), so a rewrite keeps the
        file's style; two spaces for a new file."""
        found = re.search(r"\n([ \t]+)\S", text or "")
        if found is None:
            return 2
        unit = found.group(1)
        return unit if "\t" in unit else len(unit)

    @staticmethod
    def _lenient(text: str) -> object | None:
        """The document a JSON file with `//` and `/* */` comments and trailing commas holds, or
        None when it holds none. Only ever read, to see whether an entry is already there."""
        out: list[str] = []
        comma = False  # a comma seen and not yet written: dropped before `}` or `]`
        i, end = 0, len(text)
        while i < end:
            char = text[i]
            if char.isspace():
                out.append(char)
                i += 1
            elif text.startswith("//", i):
                newline = text.find("\n", i)
                i = end if newline < 0 else newline
            elif text.startswith("/*", i):
                close = text.find("*/", i + 2)
                if close < 0:
                    return None
                out.append(" ")
                i = close + 2
            else:
                if comma and char not in "}]":
                    out.append(",")
                comma = char == ","
                if char == '"':
                    j = i + 1
                    while j < end and text[j] != '"':
                        j += 2 if text[j] == "\\" else 1
                    if j >= end:
                        return None
                    out.append(text[i : j + 1])
                    i = j + 1
                    continue
                if not comma:
                    out.append(char)
                i += 1
        try:
            document: object = json.loads("".join(out))
        except (ValueError, RecursionError):
            return None
        return document

    @staticmethod
    def _toml_carries(
        spec: HostClientSpec, parsed: Mapping[str, Any], launch: McpLaunchCommand
    ) -> bool:
        """As `_connected`, for a TOML table: a project-scope one only when it holds exactly
        `command` and `args`."""
        servers = parsed.get("mcp_servers")
        existing = servers.get(SERVER_NAME) if isinstance(servers, Mapping) else None
        if not isinstance(existing, Mapping):
            return False
        args = existing.get("args")
        if spec.scope != "user":
            return dict(existing) == {"command": launch.command, "args": list(launch.args)}
        return (
            existing.get("command") == launch.command
            and isinstance(args, list)
            and tuple(args[: len(launch.args)]) == launch.args
        )

    def _merge_toml(
        self,
        spec: HostClientSpec,
        launch: McpLaunchCommand,
        existing_content: str | None,
        target: str,
    ) -> str:
        if existing_content is None or not existing_content.strip():
            return self._toml_block(launch, [])

        try:
            parsed = tomllib.loads(existing_content)
        except (ValueError, RecursionError) as exc:
            raise HostClientError(f"{target}: invalid TOML ({exc})") from exc

        mcp_servers = parsed.get("mcp_servers")
        if mcp_servers is not None and not isinstance(mcp_servers, Mapping):
            raise HostClientError(f"{target}: 'mcp_servers' must be a TOML table")
        if self._toml_carries(spec, parsed, launch):
            return existing_content

        existing = mcp_servers.get(SERVER_NAME) if isinstance(mcp_servers, Mapping) else None
        extra = (
            self._extra_args(
                existing.get("args") if isinstance(existing, Mapping) else None, spec.protocol
            )
            if spec.scope == "user"
            else []
        )
        block = self._toml_block(launch, extra)
        if TOML_SECTION_RE.search(existing_content):
            return TOML_SECTION_RE.sub(lambda _: block, existing_content, count=1)

        trimmed = existing_content.rstrip()
        return f"{trimmed}\n\n{block}"

    @staticmethod
    def _toml_block(launch: McpLaunchCommand, extra: Sequence[str]) -> str:
        args = (*launch.args, *extra)
        return (
            "[mcp_servers.vibey]\n"
            f"command = {json.dumps(launch.command)}\n"
            f"args = [{', '.join(json.dumps(a) for a in args)}]\n"
        )


HOST_CLIENT_CATALOG: Final[HostClientsInterface] = HostClients()
