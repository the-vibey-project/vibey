# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Filesystem installer for `vibey connect`: reads host configs, writes backups, merges entries (ADR-0100).

`apply_plan` writes the way a config that may hold other servers' API keys deserves, because
`vibey acp` runs it unattended too:

- **Atomically.** The new content goes to a temporary file beside the target, which then
  replaces it (`os.replace`): a crash or a full disk never leaves a half-written config.
- **No wider than it was.** The new file keeps the old one's permission bits (a new file is
  0600), and the `.vibey.bak` copy gets the original's bits too, never the umask's 0644.
- **Through a symlink only inside home.** A target is written where it resolves to, so a
  symlinked config stays a symlink; one that sits under the home folder but resolves outside it
  is refused (`HostClientError`), and a backup path is never followed (`O_NOFOLLOW`). Every
  target of a plan is checked before any file is written.
"""

from __future__ import annotations

import os
import shutil
import stat
import sys
import tempfile
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.host_clients import HOST_CLIENT_CATALOG, ConnectPlanItem, HostClientError
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class HostInstaller:
    """Builds and applies MCP host client registration plans.

    Declared by `interfaces/host_installer_interface.py::HostInstallerInterface`.
    """

    def __init__(
        self,
        *,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        home_dir: Callable[[], Path] = Path.home,
        project_dir: Callable[[], Path] = Path.cwd,
        platform: str = sys.platform,
        which: Callable[[str], str | None] = shutil.which,
        python_executable: str = sys.executable,
    ) -> None:
        self._catalog = catalog
        self._home_dir = home_dir
        self._project_dir = project_dir
        self._platform = platform
        self._which = which
        self._python_executable = python_executable

    def build_plan(self, requested: Sequence[str] | None = None) -> tuple[ConnectPlanItem, ...]:
        specs = self._catalog.resolve_clients(requested)
        launch = self._catalog.resolve_launch(
            which_vibey=self._which("vibey"),
            python_executable=self._python_executable,
        )
        home = str(self._home_dir())
        proj = str(self._project_dir())
        items: list[ConnectPlanItem] = []
        for spec in specs:
            target = Path(
                spec.config_path(home_dir=home, project_dir=proj, platform=self._platform)
            )
            existing = target.read_text(encoding="utf-8") if target.exists() else None
            items.append(
                self._catalog.plan_one(
                    spec,
                    home_dir=home,
                    project_dir=proj,
                    platform=self._platform,
                    launch=launch,
                    existing_content=existing,
                )
            )
        return tuple(items)

    def apply_plan(self, plan: Sequence[ConnectPlanItem]) -> None:
        pending = [
            (item, self._resolved(Path(item.target_path)))
            for item in plan
            if item.action != "unchanged"
        ]
        for item, real in pending:
            real.parent.mkdir(parents=True, exist_ok=True)
            mode = 0o600
            if real.exists():
                mode = stat.S_IMODE(real.stat().st_mode)
                if item.backup_path is not None:
                    self._backup(Path(item.backup_path), real.read_text(encoding="utf-8"), mode)
            self._replace(real, item.new_content, mode)

    def _resolved(self, target: Path) -> Path:
        """Where `target` really is. A target under the home folder must resolve under it."""
        real = Path(os.path.realpath(target))
        home = Path(os.path.abspath(self._home_dir()))
        if Path(os.path.abspath(target)).is_relative_to(home) and not real.is_relative_to(
            Path(os.path.realpath(home))
        ):
            raise HostClientError(f"{target} resolves to {real}, outside your home folder")
        return real

    @staticmethod
    def _backup(path: Path, text: str, mode: int) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode)
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)

    @staticmethod
    def _replace(real: Path, text: str, mode: int) -> None:
        fd, staged = tempfile.mkstemp(dir=real.parent, prefix=f".{real.name}.", suffix=".tmp")
        try:
            os.fchmod(fd, mode)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
            os.replace(staged, real)
        except BaseException:
            Path(staged).unlink(missing_ok=True)
            raise


HOST_INSTALLER: Final[HostInstallerInterface] = HostInstaller()
