# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads, per client, which of vibey's LLM-facing surfaces are in place (SP-ACP).

`vibey connect`, `vibey doctor` and `vibey acp`'s doctor step report the same findings
(`domain/llm_tooling.py`). This adapter only reads, and it reads like a file it does not trust,
because some of what it reads is: a project-scope client's config (Claude Code's `.mcp.json`,
VS Code's `.vscode/mcp.json`) is a file in whatever folder vibey runs in -- for `vibey acp`, the
repository an editor opened.

- **Never through a symbolic link.** A config file or Claude Code's plugin record that is a
  link is reported, not read (`O_NOFOLLOW`), as `vibey connect` refuses to write through one.
- **Regular files only, bounded.** It opens with `O_NONBLOCK` and reads only a regular file of
  at most `MAX_BYTES`: a FIFO or a device in a config's place is reported, never read.
- **Inside the scope's root only.** A config whose folder resolves (symlinks followed) outside
  the home folder (user scope) or the project folder (project scope) is reported, not read.
- **The entry `vibey connect` would write.** An entry counts as present only when it is exactly
  what `vibey connect` writes now, with the same pinned launcher (the running install's own
  `vibey`, or the Python fallback), so a config pointing at another `vibey` says so.

Declared by `interfaces/llm_tooling_probe_interface.py`.
"""

from __future__ import annotations

import errno
import importlib.resources
import json
import os
import shlex
import stat
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.host_clients import HOST_CLIENT_CATALOG, HostClientError, HostClientSpec
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.domain.interfaces.llm_tooling_interface import LlmToolingInterface
from vibey.domain.llm_tooling import (
    LLM_TOOLING,
    PLUGIN_ID,
    SKILL_NAME,
    ClientTooling,
    EntryState,
    ToolingFinding,
)

PLUGIN_RECORD: Final = Path(".claude") / "plugins" / "installed_plugins.json"
"""Where Claude Code records the plugins it installed, under the home folder."""
SKILL_FOLDERS: Final[dict[str, Path]] = {
    "claude_code": Path(".claude") / "skills",
    "codex": Path(".codex") / "skills",
}
"""The user-level skills folder of each client that reads one, under the home folder."""
REPOSITORY_SKILL: Final = (
    f"copy .agents/skills/{SKILL_NAME} from https://github.com/the-vibey-project/vibey "
    "into ~/.codex/skills/"
)


class LlmToolingProbe:
    """Declared by `interfaces/llm_tooling_probe_interface.py::LlmToolingProbeInterface`."""

    MAX_BYTES: Final = 1 << 20

    def __init__(
        self,
        *,
        launcher: Callable[[], str | None],
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        tooling: LlmToolingInterface = LLM_TOOLING,
        home_dir: Callable[[], Path] = Path.home,
        project_dir: Callable[[], Path] = Path.cwd,
        platform: str = sys.platform,
        python_executable: str = sys.executable,
        shipped_skill: Callable[[], Path | None] | None = None,
    ) -> None:
        self._launcher = launcher
        self._catalog = catalog
        self._tooling = tooling
        self._home_dir = home_dir
        self._project_dir = project_dir
        self._platform = platform
        self._python = python_executable
        self._shipped = shipped_skill or self.shipped_skill

    def detected(self) -> tuple[HostClientSpec, ...]:
        home = str(self._home_dir())
        return tuple(
            spec
            for spec in self._catalog.all()
            if Path(spec.presence_path(home_dir=home, platform=self._platform)).is_dir()
        )

    def findings(self, client_ids: Sequence[str] | None = None) -> tuple[ToolingFinding, ...]:
        specs = self._catalog.resolve_clients(client_ids) if client_ids else self.detected()
        home, project = self._home_dir(), self._project_dir()
        launcher = self._launcher()
        plugin = self._plugin_installed(home)
        install = self._skill_install()
        found: list[ToolingFinding] = []
        for spec in specs:
            entry, detail = self._entry(spec, launcher, home, project)
            tooling = ClientTooling(
                entry,
                detail,
                plugin_installed=plugin and spec.client_id == "claude_code",
                skill_at=self._skill_at(spec, home),
                skill_install=install,
            )
            found.extend(self._tooling.findings(spec, tooling))
        return tuple(found)

    @staticmethod
    def shipped_skill() -> Path | None:
        """The `vibey-chat-driver` skill folder this install carries: in the wheel
        (`vibey_skills/plugins/...`), or in the source tree an editable install runs from."""
        try:
            package = Path(str(importlib.resources.files("vibey_skills")))
        except ModuleNotFoundError:  # pragma: no cover - vibey-engine always ships vibey_skills
            return None
        within = Path("plugins") / "vibey" / "skills" / SKILL_NAME
        for root in (package, package.parent.parent):
            if (root / within / "SKILL.md").is_file():
                return root / within
        return None  # pragma: no cover - a broken install

    def _entry(
        self, spec: HostClientSpec, launcher: str | None, home: Path, project: Path
    ) -> tuple[EntryState, str]:
        target = Path(
            spec.config_path(home_dir=str(home), project_dir=str(project), platform=self._platform)
        )
        shown = self._shown(target, home)
        root, where = (
            (home, "your home folder") if spec.scope == "user" else (project, "the project folder")
        )
        if not Path(os.path.realpath(target.parent)).is_relative_to(os.path.realpath(root)):
            return "refused", f"{shown} is not inside {where}; vibey neither reads nor writes it"
        text, refused = self._read(target, shown)
        if refused is not None:
            return "refused", refused
        if text is None:
            return "missing", f"no {shown}"
        launch = self._catalog.resolve_launch(
            which_vibey=launcher, python_executable=self._python, protocol=spec.protocol
        )
        if self._catalog.carries(spec, launch, text):
            return "present", f"in {shown}"
        try:
            self._catalog.plan_one(
                spec,
                home_dir=str(home),
                project_dir=str(project),
                platform=self._platform,
                launch=launch,
                existing_content=text,
            )
        except HostClientError as exc:
            return "refused", str(exc).replace(str(target), shown)
        return "missing", f"{shown} does not carry the entry `vibey connect` writes"

    def _read(self, path: Path, shown: str) -> tuple[str | None, str | None]:
        """The file's text (None when there is no file), or why it is not read."""
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None, None
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                return None, f"{shown} is a symbolic link; vibey does not read or write through one"
            return None, f"{shown} cannot be read ({exc.strerror})"
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode):
                return None, f"{shown} is not a regular file; vibey does not read it"
            data = handle.read(self.MAX_BYTES + 1)
        if len(data) > self.MAX_BYTES:
            return None, f"{shown} is larger than {self.MAX_BYTES} bytes; vibey does not read it"
        try:
            return data.decode("utf-8"), None
        except UnicodeDecodeError:
            return None, f"{shown} is not UTF-8 text"

    def _plugin_installed(self, home: Path) -> bool:
        """Whether Claude Code records `vibey@vibey` (the plugin from the marketplace named
        `vibey`, this repository's root marketplace) as installed."""
        text, _ = self._read(home / PLUGIN_RECORD, "")
        if text is None:
            return False
        try:
            record = json.loads(text)
        except ValueError:
            return False
        plugins = record.get("plugins") if isinstance(record, dict) else None
        return isinstance(plugins, dict) and PLUGIN_ID in plugins

    def _skill_at(self, spec: HostClientSpec, home: Path) -> str | None:
        folder = SKILL_FOLDERS.get(spec.client_id)
        if folder is None:
            return None
        skill = home / folder / SKILL_NAME
        return self._shown(skill, home) if (skill / "SKILL.md").is_file() else None

    def _skill_install(self) -> str:
        shipped = self._shipped()
        if shipped is None:
            return REPOSITORY_SKILL
        return f"mkdir -p ~/.codex/skills && cp -R {shlex.quote(str(shipped))} ~/.codex/skills/"

    @staticmethod
    def _shown(path: Path, home: Path) -> str:
        """`path` as a person reads it: `~/...` under the home folder."""
        return f"~/{path.relative_to(home)}" if path.is_relative_to(home) else str(path)
