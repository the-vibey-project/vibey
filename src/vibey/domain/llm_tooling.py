# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which of vibey's LLM-facing surfaces each client has, and what to do about one it lacks (SP-ACP).

A frontier client reaches vibey through up to four surfaces, each shipped by this family:

- **`acp-agent`**: the ACP agent entry `vibey connect` writes (Zed's `agent_servers.vibey`).
- **`mcp-server`**: the MCP server entry `vibey connect` writes (every other client's
  `vibey mcp`), or, for Claude Code, the `vibey` plugin, whose `.mcp.json` registers it too.
- **`skill`**: the `vibey-chat-driver` skill, where the client reads skills from a folder vibey's
  trees fill: Claude Code (the `vibey` plugin, or `~/.claude/skills`) and Codex
  (`~/.codex/skills`, the family's `.agents/skills` tree).
- **`plugin`**: the `vibey` plugin from the root marketplace (`.claude-plugin/marketplace.json`,
  ADR-0034), which only Claude Code installs.

`vibey connect` installs the two entry surfaces itself. The skill and the plugin are installed by
the client's own command; vibey reports them, with that exact command, and never invents an
installer the family does not ship. A surface a client cannot have is `not-applicable`.

Pure: what was found on disk comes in as a `ClientTooling`, read by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from vibey.domain.host_clients import HostClientSpec
from vibey.domain.interfaces.llm_tooling_interface import LlmToolingInterface

ToolingSurface = Literal["acp-agent", "mcp-server", "skill", "plugin"]
SurfaceState = Literal["present", "missing", "not-applicable"]
EntryState = Literal["present", "missing", "foreign", "refused"]
"""`foreign`: the file holds a `vibey` entry that is not the one `vibey connect` writes (in a
project's file, anything but the exact canonical entry). It is never excused by the plugin."""

SURFACES: Final[tuple[ToolingSurface, ...]] = ("acp-agent", "mcp-server", "skill", "plugin")
SKILL_NAME: Final = "vibey-chat-driver"
PLUGIN_ID: Final = "vibey@vibey"
"""The plugin as Claude Code records it: plugin `vibey` from the marketplace named `vibey`."""
PLUGIN_COMMANDS: Final = (
    "in Claude Code run /plugin marketplace add the-vibey-project/vibey, "
    "then /plugin install vibey@vibey"
)
SKILL_CLIENTS: Final = frozenset({"claude_code", "codex"})
PLUGIN_CLIENTS: Final = frozenset({"claude_code"})
MARKS: Final[dict[SurfaceState, str]] = {
    "present": "PASS",
    "missing": "WARN",
    "not-applicable": "UNKNOWN",
}


@dataclass(frozen=True, slots=True)
class ClientTooling:
    """What the caller found on disk for one client.

    `entry` is the state of its `vibey` entry, `entry_detail` where it is or why it is missing
    or refused (a refusal carries the snippet to paste); `plugin_installed` whether Claude
    Code records `vibey@vibey`; `skill_at` where the skill was found, if anywhere; and
    `skill_install` the exact command that puts the skill in place for a client vibey cannot
    reach through a plugin.
    """

    entry: EntryState
    entry_detail: str
    plugin_installed: bool = False
    skill_at: str | None = None
    skill_install: str = ""


@dataclass(frozen=True, slots=True)
class ToolingFinding:
    """One client's one surface."""

    client_id: str
    surface: ToolingSurface
    state: SurfaceState
    detail: str

    @property
    def mark(self) -> str:
        """As `vibey doctor` marks it: present `PASS`, missing `WARN`, not applicable
        `UNKNOWN`. A missing surface never fails doctor."""
        return MARKS[self.state]

    @property
    def name(self) -> str:
        return f"{self.client_id}:{self.surface}"


class LlmTooling:
    """Declared by `interfaces/llm_tooling_interface.py::LlmToolingInterface`."""

    def findings(self, spec: HostClientSpec, found: ClientTooling) -> tuple[ToolingFinding, ...]:
        return (
            self._entry(spec, found, "acp-agent", wanted="acp"),
            self._entry(spec, found, "mcp-server", wanted="mcp"),
            self._skill(spec, found),
            self._plugin(spec, found),
        )

    @staticmethod
    def _entry(
        spec: HostClientSpec, found: ClientTooling, surface: ToolingSurface, *, wanted: str
    ) -> ToolingFinding:
        if spec.protocol != wanted:
            other = spec.protocol.upper()
            return ToolingFinding(
                spec.client_id,
                surface,
                "not-applicable",
                f"{spec.label} reaches vibey over {other}",
            )
        if found.entry == "present":
            return ToolingFinding(spec.client_id, surface, "present", found.entry_detail)
        if surface == "mcp-server" and found.plugin_installed and found.entry == "missing":
            return ToolingFinding(
                spec.client_id, surface, "present", f"through the plugin {PLUGIN_ID}"
            )
        if found.entry == "refused":
            return ToolingFinding(spec.client_id, surface, "missing", found.entry_detail)
        return ToolingFinding(
            spec.client_id,
            surface,
            "missing",
            f"{found.entry_detail}; run `vibey connect --client {spec.client_id}`",
        )

    @staticmethod
    def _skill(spec: HostClientSpec, found: ClientTooling) -> ToolingFinding:
        if spec.client_id not in SKILL_CLIENTS:
            return ToolingFinding(
                spec.client_id,
                "skill",
                "not-applicable",
                f"vibey ships no {SKILL_NAME} skill folder {spec.label} reads",
            )
        if found.plugin_installed:
            return ToolingFinding(
                spec.client_id, "skill", "present", f"{SKILL_NAME} in the plugin {PLUGIN_ID}"
            )
        if found.skill_at is not None:
            return ToolingFinding(spec.client_id, "skill", "present", found.skill_at)
        how = PLUGIN_COMMANDS if spec.client_id in PLUGIN_CLIENTS else found.skill_install
        return ToolingFinding(spec.client_id, "skill", "missing", f"{SKILL_NAME}: {how}")

    @staticmethod
    def _plugin(spec: HostClientSpec, found: ClientTooling) -> ToolingFinding:
        if spec.client_id not in PLUGIN_CLIENTS:
            return ToolingFinding(
                spec.client_id,
                "plugin",
                "not-applicable",
                f"the vibey marketplace's plugins are for Claude Code, not {spec.label}",
            )
        if found.plugin_installed:
            return ToolingFinding(spec.client_id, "plugin", "present", f"{PLUGIN_ID} installed")
        return ToolingFinding(spec.client_id, "plugin", "missing", PLUGIN_COMMANDS)


LLM_TOOLING: Final[LlmToolingInterface] = LlmTooling()
