# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The loop capability bundle, read strictly from a `[loops]` table (SP-LOOPS Task 3).

```toml
[loops]
plugins = ["currency-research@vibey", "linting@acme"]   # name@marketplace; absent = research
skills = ["research-search-and-source-quality"]          # skills every loop is pointed at
disable = ["old-skill"]                                  # plugins, servers or skills to drop
builtin_web = false                                      # the engine's own web tools (R4)
instruction_files = ["CLAUDE.md", "AGENTS.md"]           # read from the run's folder (R8)
instruction_max_bytes = 65536                            # larger ones are named, not inlined
snapshot_max_age_days = 7                                # when a worker sweeps old snapshots

[[loops.marketplaces]]
name = "acme"
source = "https://example.test/acme.git"                 # a git or https URL, or a local folder
ref = "v1.2.0"                                           # optional pin

[[loops.mcp_servers]]
name = "files"
trust = "local"                                          # local: stdio, needs `command`
command = ["fake-mcp", "--stdio"]
env_allow = ["HOME"]                                     # the only variables it keeps (never a secret)

[[loops.mcp_servers]]
name = "tickets"
trust = "remote"                                         # remote: HTTPS, needs `url`
url = "https://mcp.example.test/v1"
```

Every key, at every level, is known or refused, and a refusal names the key path
(`BundleError`), so a typo never silently drops a capability. Names are plain identifiers (they
later become folder names and lock keys), sources and refs can never be read as a command-line
option, lists are capped, and the marketplace name `vibey` is reserved for the copy that ships in
the wheel. `builtin_web`, `instruction_files` and `instruction_max_bytes` are part of what a loop
is given (SP-LOOPS Phase 4, R13), so they enter the snapshot's digest; `snapshot_max_age_days` is
housekeeping and does not. Like every key but `disable`, they come only from the person's own
file. Declared by `interfaces/bundle_interface.py::BundleSpecInterface`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Final
from urllib.parse import urlsplit

from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.defaults import (
    DEFAULT_MARKETPLACE_NAME,
    DEFAULT_RESEARCH_PLUGINS,
)
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec, McpTrust
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.plugin_spec import PluginSpec

MAX_ENTRIES: Final = 256
"""The most entries any one `[loops]` list may hold."""
MAX_TEXT: Final = 4096
"""The longest a source, ref, URL or command argument may be, in characters."""

_ROOT: Final = "loops"
_KEYS: Final = frozenset(
    {
        "marketplaces",
        "plugins",
        "mcp_servers",
        "skills",
        "disable",
        "builtin_web",
        "instruction_files",
        "instruction_max_bytes",
        "snapshot_max_age_days",
    }
)
DEFAULT_INSTRUCTION_FILES: Final = ("CLAUDE.md", "AGENTS.md")
"""The instruction files a loop reads from its run's folder when `[loops]` names none (R8)."""
INSTRUCTION_FILES_MAX: Final = 16
"""The most instruction files `[loops] instruction_files` may name."""
DEFAULT_INSTRUCTION_MAX_BYTES: Final = 65536
"""The largest instruction file inlined into a loop's system prompt; a larger one is named, with
its size, for the agent to read (R8: never truncated)."""
INSTRUCTION_MAX_BYTES_CEILING: Final = 1024 * 1024
"""The most `[loops] instruction_max_bytes` may be: 1 MiB."""
DEFAULT_SNAPSHOT_MAX_AGE_DAYS: Final = 7
"""How old, in days, a run's snapshot folder may be before a worker's sweep removes it (R10)."""
_MARKETPLACE_KEYS: Final = frozenset({"name", "source", "ref"})
_SERVER_KEYS: Final = frozenset({"name", "trust", "command", "url", "env_allow"})
_TRUST: Final[tuple[McpTrust, ...]] = ("local", "remote")
_ENV_NAME: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")
SECRET_ENV_NAMES: Final = frozenset(
    {
        "VIBEY_HUB_TOKEN",
        "VIBEY_AGENT_TOKEN",
        "VIBEY_BRAVE_API_KEY",
        "BRAVE_SEARCH_API_KEY",
        "WEBSEARCH_BRAVE_API_KEY",
    }
)
"""Variables that carry the host token, the agent token or a Brave key, named outright."""
SECRET_ENV_PATTERN: Final = re.compile(r"TOKEN|SECRET|PASSWORD|API_KEY|_KEY$|BRAVE", re.I)
"""Any other variable named like a secret: a local MCP server's output reaches the model, so it
never keeps one (Global Constraint 3: a loop never receives the host or agent token or a Brave
key)."""


@dataclass(frozen=True, slots=True)
class BundleSpec:
    """Declared by `interfaces/bundle_interface.py::BundleSpecInterface`."""

    marketplaces: tuple[MarketplaceSpec, ...]
    plugins: tuple[PluginSpec, ...]
    mcp_servers: tuple[McpServerSpec, ...]
    skills: tuple[str, ...]
    disabled: frozenset[str]
    builtin_web: bool = False
    instruction_files: tuple[str, ...] = DEFAULT_INSTRUCTION_FILES
    instruction_max_bytes: int = DEFAULT_INSTRUCTION_MAX_BYTES
    snapshot_max_age_days: int = DEFAULT_SNAPSHOT_MAX_AGE_DAYS

    @classmethod
    def default(cls) -> BundleSpec:
        """The bundle of a person who wrote no `[loops]`: the research plugins, nothing else; the
        engine's own web tools off, `CLAUDE.md` and `AGENTS.md` read up to 64 KiB, and snapshots
        swept after a week."""
        return cls.from_mapping({})

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> BundleSpec:
        """`raw` is the `[loops]` table's contents. Raises `BundleError` naming the key path."""
        cls._known(raw, _KEYS, _ROOT)
        marketplaces = cls._marketplaces(raw.get("marketplaces", []))
        declared = {spec.name for spec in marketplaces} | {DEFAULT_MARKETPLACE_NAME}
        if "plugins" in raw:
            plugins = cls._plugins(raw["plugins"], declared)
        else:
            plugins = tuple(
                PluginSpec(n, DEFAULT_MARKETPLACE_NAME) for n in DEFAULT_RESEARCH_PLUGINS
            )
        bundle = cls(
            marketplaces=marketplaces,
            plugins=plugins,
            mcp_servers=cls._servers(raw.get("mcp_servers", [])),
            skills=cls._names(raw.get("skills", []), f"{_ROOT}.skills"),
            disabled=frozenset(),
            builtin_web=cls._bool(raw.get("builtin_web", False), f"{_ROOT}.builtin_web"),
            instruction_files=cls._instruction_files(
                raw.get("instruction_files", list(DEFAULT_INSTRUCTION_FILES))
            ),
            instruction_max_bytes=cls._whole(
                raw.get("instruction_max_bytes", DEFAULT_INSTRUCTION_MAX_BYTES),
                f"{_ROOT}.instruction_max_bytes",
                1,
                INSTRUCTION_MAX_BYTES_CEILING,
            ),
            snapshot_max_age_days=cls._whole(
                raw.get("snapshot_max_age_days", DEFAULT_SNAPSHOT_MAX_AGE_DAYS),
                f"{_ROOT}.snapshot_max_age_days",
                1,
                None,
            ),
        )
        return bundle.narrowed_by(cls.disable_names(raw.get("disable", [])))

    @classmethod
    def disable_names(cls, raw: object) -> tuple[str, ...]:
        """A `disable` list, from the person's file or a project's, held to one rule: a list of
        at most `MAX_ENTRIES` plain names, each once. Raises `BundleError` at `loops.disable`."""
        return cls._names(raw, f"{_ROOT}.disable")

    def narrowed_by(self, disabled: Iterable[str]) -> BundleSpec:
        off = frozenset(disabled)
        return replace(
            self,
            plugins=tuple(p for p in self.plugins if p.name not in off),
            mcp_servers=tuple(s for s in self.mcp_servers if s.name not in off),
            skills=tuple(s for s in self.skills if s not in off),
            disabled=self.disabled | off,
        )

    # -- the strict reading, one helper per shape ------------------------------------------

    @staticmethod
    def _known(table: Mapping[str, object], known: frozenset[str], path: str) -> None:
        unknown = sorted(set(table) - known)
        if unknown:
            raise BundleError(f"{path}.{unknown[0]}", "is not a known key")

    @staticmethod
    def _list(value: object, path: str) -> Sequence[object]:
        if not isinstance(value, list | tuple):
            raise BundleError(path, "must be a list")
        if len(value) > MAX_ENTRIES:
            raise BundleError(path, f"must hold at most {MAX_ENTRIES} entries")
        return value

    @classmethod
    def _tables(cls, value: object, path: str) -> list[tuple[str, Mapping[str, object]]]:
        tables: list[tuple[str, Mapping[str, object]]] = []
        for index, entry in enumerate(cls._list(value, path)):
            where = f"{path}[{index}]"
            if not isinstance(entry, Mapping):
                raise BundleError(where, "must be a table")
            tables.append((where, entry))
        return tables

    @staticmethod
    def _name(value: object, path: str) -> str:
        if not isinstance(value, str) or NAME_PATTERN.fullmatch(value) is None:
            raise BundleError(
                path,
                "must be a name of letters, digits, '.', '_' or '-', starting with a letter or "
                "digit, at most 128 characters",
            )
        return value

    @staticmethod
    def _text(value: object, path: str) -> str:
        """A source, ref, URL or argument: a bounded, printable string."""
        if not isinstance(value, str) or not value:
            raise BundleError(path, "must be a non-empty string")
        if len(value) > MAX_TEXT:
            raise BundleError(path, f"must be at most {MAX_TEXT} characters")
        if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
            raise BundleError(path, "must not contain control characters")
        return value

    @classmethod
    def option_safe_text(cls, value: object, path: str) -> str:
        """A source or ref anywhere (the bundle, the lock): non-empty, at most `MAX_TEXT`
        characters, no control characters, never starting with `-`. Raises `BundleError`."""
        return cls._not_an_option(value, path)

    @classmethod
    def _not_an_option(cls, value: object, path: str) -> str:
        text = cls._text(value, path)
        if text.startswith("-"):
            raise BundleError(path, "must not start with '-' (it would be read as an option)")
        return text

    @classmethod
    def _names(cls, value: object, path: str) -> tuple[str, ...]:
        names: list[str] = []
        for index, entry in enumerate(cls._list(value, path)):
            where = f"{path}[{index}]"
            name = cls._name(entry, where)
            if name in names:
                raise BundleError(where, f"names {name} twice")
            names.append(name)
        return tuple(names)

    @staticmethod
    def _bool(value: object, path: str) -> bool:
        if not isinstance(value, bool):
            raise BundleError(path, "must be true or false")
        return value

    @staticmethod
    def _whole(value: object, path: str, least: int, most: int | None) -> int:
        """A whole number from `least` to `most` (no ceiling when `most` is None); a TOML
        boolean is not one, though Python counts it as an int."""
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < least
            or (most is not None and value > most)
        ):
            span = f"at least {least}" if most is None else f"between {least} and {most}"
            raise BundleError(path, f"must be a whole number, {span}")
        return value

    @classmethod
    def _instruction_files(cls, value: object) -> tuple[str, ...]:
        """Plain file names, read only from the run's own folder: a name is never a path."""
        path = f"{_ROOT}.instruction_files"
        names = cls._names(value, path)
        if len(names) > INSTRUCTION_FILES_MAX:
            raise BundleError(path, f"must hold at most {INSTRUCTION_FILES_MAX} entries")
        return names

    @classmethod
    def _marketplaces(cls, value: object) -> tuple[MarketplaceSpec, ...]:
        specs: list[MarketplaceSpec] = []
        for where, table in cls._tables(value, f"{_ROOT}.marketplaces"):
            cls._known(table, _MARKETPLACE_KEYS, where)
            name = cls._name(table.get("name"), f"{where}.name")
            if name == DEFAULT_MARKETPLACE_NAME:
                raise BundleError(
                    f"{where}.name", f"{name} is reserved for the marketplace that ships with vibey"
                )
            if any(spec.name == name for spec in specs):
                raise BundleError(f"{where}.name", f"declares the marketplace {name} twice")
            source = cls._not_an_option(table.get("source"), f"{where}.source")
            ref = None
            if "ref" in table:
                ref = cls._not_an_option(table["ref"], f"{where}.ref")
            specs.append(MarketplaceSpec(name, source, ref))
        return tuple(specs)

    @classmethod
    def _plugins(cls, value: object, declared: set[str]) -> tuple[PluginSpec, ...]:
        specs: list[PluginSpec] = []
        path = f"{_ROOT}.plugins"
        for index, entry in enumerate(cls._list(value, path)):
            where = f"{path}[{index}]"
            parts = entry.split("@") if isinstance(entry, str) else []
            if len(parts) != 2 or not all(NAME_PATTERN.fullmatch(part) for part in parts):
                raise BundleError(where, "must be written name@marketplace")
            name, marketplace = parts
            if marketplace not in declared:
                raise BundleError(
                    where, f"names the marketplace {marketplace}, which [loops] does not declare"
                )
            if any(spec.name == name for spec in specs):
                raise BundleError(where, f"names the plugin {name} twice")
            specs.append(PluginSpec(name, marketplace))
        return tuple(specs)

    @classmethod
    def _servers(cls, value: object) -> tuple[McpServerSpec, ...]:
        specs: list[McpServerSpec] = []
        for where, table in cls._tables(value, f"{_ROOT}.mcp_servers"):
            cls._known(table, _SERVER_KEYS, where)
            name = cls._name(table.get("name"), f"{where}.name")
            if any(spec.name == name for spec in specs):
                raise BundleError(f"{where}.name", f"declares the MCP server {name} twice")
            trust = cls._trust(table.get("trust"), f"{where}.trust")
            command: tuple[str, ...] | None = None
            url: str | None = None
            if trust == "local":
                if "url" in table:
                    raise BundleError(f"{where}.url", "is for a remote server, not a local one")
                command = cls._command(table.get("command"), f"{where}.command")
            else:
                if "command" in table:
                    raise BundleError(f"{where}.command", "is for a local server, not a remote one")
                url = cls._https(table.get("url"), f"{where}.url")
            env_allow = cls._env_allow(table.get("env_allow", []), f"{where}.env_allow")
            specs.append(McpServerSpec(name, trust, command, url, env_allow))
        return tuple(specs)

    @staticmethod
    def _trust(value: object, path: str) -> McpTrust:
        for trust in _TRUST:
            if value == trust:
                return trust
        raise BundleError(path, "must be local or remote")

    @classmethod
    def _command(cls, value: object, path: str) -> tuple[str, ...]:
        if value is None:
            raise BundleError(path, "is required for a local server")
        if not isinstance(value, list | tuple) or not value:
            raise BundleError(path, "must be a non-empty list of strings (the argv)")
        if len(value) > MAX_ENTRIES:
            raise BundleError(path, f"must hold at most {MAX_ENTRIES} arguments")
        return tuple(cls._text(argument, path) for argument in value)

    @classmethod
    def _https(cls, value: object, path: str) -> str:
        if value is None:
            raise BundleError(path, "is required for a remote server")
        url = cls._text(value, path)
        try:
            # urlsplit, and the hostname, port and userinfo reads, raise ValueError for a
            # malformed bracketed host or a port that is not a number in range.
            parts = urlsplit(url)
            host, port = parts.hostname, parts.port
            credentials = parts.username is not None or parts.password is not None
        except ValueError as exc:
            raise BundleError(path, "must be an https:// URL with a host") from exc
        if parts.scheme != "https" or not host or any(c.isspace() for c in parts.netloc):
            raise BundleError(path, "must be an https:// URL with a host")
        if port == 0:
            raise BundleError(path, "must not name port 0")
        if credentials:
            raise BundleError(path, "must not carry credentials")
        return url

    @classmethod
    def _env_allow(cls, value: object, path: str) -> tuple[str, ...]:
        names = cls._list(value, path)
        if not all(isinstance(n, str) and _ENV_NAME.fullmatch(n) for n in names):
            raise BundleError(path, "must be a list of environment variable names")
        for index, name in enumerate(names):
            text = str(name)
            if text.upper() in SECRET_ENV_NAMES or SECRET_ENV_PATTERN.search(text):
                raise BundleError(
                    f"{path}[{index}]",
                    "names a variable that carries a secret (a token, key or password); a "
                    "server never keeps one, since what it prints reaches the model",
                )
        return tuple(str(n) for n in names)
